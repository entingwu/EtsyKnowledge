# item_name 的流转：从导入到检索过滤

> 版本：2026-10-20 · 相关代码：`import_process/nodes/node_item_name_recognition.py`、`query_process/nodes/node_item_name_confirm.py`、`query_process/nodes/node_search_embedding.py`

## 0. 一句话结论

- 导入时，大模型给每份文件识别**一次** `item_name`，同一个字符串同时写进 **item_name 表**和该文件所有 **chunk** 的 `item_name` 字段。
- 查询时，先用大模型提取用户口中的商品名，再去 item_name 表**混合检索**，取回库里存的原样 `item_name`（名称对齐）。
- 对齐后的标准名作为 `expr = item_name in [...]`，在 chunks 表里**精确过滤**，只取这个商品的切片。

```
查询阶段
  node_item_name_confirm
    └─ 输出 item_names = ["Birth Flower Cufflinks Gold Groom"]
       这个名字来自 item_name 表里存的 item_name 字段，和 chunks 里回填的值完全一样
          ↓  经过 main_graph 的路由：answer 为空才继续往下走
  node_search_embedding
    └─ 用 rewritten_query 检索 chunks，并用 expr = item_name in [...] 过滤
```

`align_item_names` 得出的 `final_item_names` 就是过滤条件的来源。它取的是 Milvus 商品名表里存的 `item_name` 字段，不是大模型生成的名字，所以能和 chunks 里回填的 `item_name` 精确匹配。这正是要先做"名称对齐"的原因：大模型说的 "Birth Flower Cufflinks" 拿去做 `in` 过滤会一条都匹配不到，必须先换成库里的标准名。

---

## 1. 实测验证

以 `001_4565343414_cufflinks-gold-groom` 为例，直接查 Milvus：

```
item_name 表:  item_name     = 'Birth Flower Cufflinks Gold Groom'
               file_title    = '001_4565343414_cufflinks-gold-groom'
               listing_title = 'Birth Flower Cufflinks – Gold, Groom'

chunks 表 item_name in ["Birth Flower Cufflinks Gold Groom"] → 45 条，全部来自 001
chunks 表 item_name in ["Birth Flower Cufflinks"]            → 0 条
```

最后一行说明为什么必须先对齐：只差两个词，精确过滤就一条都匹配不到。

---

## 2. 导入阶段：同一个字符串写进两张表

导入图顺序（`import_process/main_graph.py`）：

```
NodeEntry → NodePDFToMD → NodeMDImg → NodeDocumentSplit → NodeItemNameRecognition → NodeBGEEmbedding → NodeImportMilvus
```

**① 大模型只生成一次**（`NodeItemNameRecognition.process`）

```python
item_name = self.get_item_name(file_title, context)
# context = listing_title = "Birth Flower Cufflinks – Gold, Groom"
# → item_name = "Birth Flower Cufflinks Gold Groom"
```

`context` 优先用 markdown 一级标题里的 listing 标题（`get_listing_title`），拿不到再拼前 15 个 chunk 的内容（`get_chunks_str`，上限 10000 字符）。prompt 是 `ITEM_NAME_SYSTEM_PROMPT` / `ITEM_NAME_USER_PROMPT_TEMPLATE`，识别结果为空时用 `file_title` 兜底。

**② 写进 item_name 表**（`insert_data`），每份文件一条：

```python
embeddings = get_bge_embeddings([listing_title or item_name])
data = {"item_name": item_name, "listing_title": listing_title, "listing_id": listing_id,
        "file_title": file_title, "dense_vector": ..., "sparse_vector": ...}
milvus_client.insert(collection_name=MilvusConfig.item_name_collection, data=data)
```

注意向量化的文本是 **`listing_title`**（拿不到才用 `item_name`），不是 `item_name` 本身。listing 标题比 3–8 个词的商品名信息更全，查询时大模型给出的短名（"Birth Flower Cufflinks"）实际上是在和完整标题（"Birth Flower Cufflinks – Gold, Groom"）比相似度。`item_name` 字段只作为对齐后取回的标准名和过滤值。

**③ 同一个变量回填到每个 chunk**（`insert_data`）：

```python
for chunk in chunks:
    chunk["item_name"] = item_name
```

**④ chunk 写进 chunks 表**（`NodeImportMilvus`），`item_name` 作为字段一起入库：

```python
milvus_client.insert(collection_name=MilvusConfig.chunks_collection, data=chunks)
```

另外，`NodeBGEEmbedding.get_embedding_text` 向量化 chunk 时会把商品名拼在内容前面（`f"{item_name}\n{content}"`），让每个 chunk 的向量也带上商品信息。

两边一字不差，是因为 ② 和 ③ 用的是**同一个 Python 变量**，大模型只调用了一次。

```
                 ┌──────────────────────────────────────┐
                 │ item_name = "Birth Flower Cufflinks   │
                 │              Gold Groom"              │
                 └───────────┬──────────────┬────────────┘
                             │              │
              ┌──────────────▼───┐   ┌──────▼─────────────────────┐
              │ item_name 表      │   │ chunks 表（45 条）           │
              │ 1 条 + 向量        │   │ 每条都有 item_name 字段      │
              │ 用来：名称对齐      │   │ 用来：检索时过滤             │
              └──────────────────┘   └────────────────────────────┘
```

---

## 3. 查询阶段：把用户的叫法换成库里的标准名

示例对话：

```
user:      Please Introduce Birth Flower Cufflinks
assistant: Hi, which one do you like?
user:      Birth Flower Cufflinks Gold Groom
assistant: Any specific questions?
user:      How to use?          ← 当前问题
```

**① 大模型提取粗略的名字**（`get_item_names`）

```python
item_names = ["Birth Flower Cufflinks"]      # 用户的叫法，不是库里的名字
rewritten_query = "How to use the Birth Flower Cufflinks?"
```

**② 去 item_name 表混合检索**（`hybrid_search_item_names`）

```python
"search_item_name": search_item_name_dict.get("entity", {}).get("item_name")
```

这一行是关键：`search_item_name` 是从 Milvus 的 `entity` 里直接取出的 `item_name` 字段，也就是导入时存进去的原样字符串。实测分数：

```
0.8510  'Birth Flower Cufflinks' -> 'Birth Flower Cufflinks Gold Groom'
0.8332  'Birth Flower Cufflinks' -> 'Birth Flower Cufflinks Gold Dad'
0.8148  'Birth Flower Cufflinks' -> 'Birth Flower Cufflinks for Dad'
...
0.6682  'Birth Flower Cufflinks' -> 'Silver Heart Birthstone Cufflinks'
```

**③ 按分数对齐**（`align_item_names`）

```python
final_item_names = ['Birth Flower Cufflinks Gold Groom']   # 分数 ≥ 0.85
answer = ''
```

对齐按大模型给出的**每个原始名分组**进行：某个原始名有 ≥ 0.85 的结果就算确认，否则它的 0.6 ~ 0.85 结果作为可选项。只要有任何一个原始名停留在可选项，就反问用户（已确认的名字仍写进 `final_item_names` 和历史记录）。确认名和可选项都会去重，已确认的名字不会再出现在可选项里。

**④ 写回图状态**（`process` 的 return）

```python
"item_names": final_item_names,      # 覆盖掉大模型的粗略名字
"rewritten_query": rewritten_query,
"answer": answer,
```

此后图状态里的 `item_names` 已经是库里的标准名，大模型的 "Birth Flower Cufflinks" 只留在节点内部，不会传到下游。

**⑤ 路由**（`query_process/main_graph.py` 的 `after_item_name_confirm_router`）

```python
def after_item_name_confirm_router(self, state):
    answer = state.get("answer", "")
    if answer:                          # 没确认商品（需要反问或识别不到）
        return NodeAnswerOutput.name    #  → 直接回复，不检索
    else:                               # 商品已确认
        return [NodeSearchEmbeddingHyde.name, NodeSearchEmbedding.name, NodeWebSearchMcp.name]
```

| `align_item_names` 结果 | answer | 去向 |
|---|---|---|
| 每个原始名要么确认（≥ 0.85）、要么全是噪音，且至少一个确认 | `''` | 3 个检索节点并行 |
| 有原始名只有可选的名字（0.6 ~ 0.85） | `"Which of these products..."` | 直接回复，让用户选 |
| 全是噪音（< 0.6），或大模型没提取到名字 / 返回无法解析的 JSON | `"Sorry, we couldn't identify..."` | 直接回复，让用户重新提问 |

**⑥ 用标准名过滤 chunks**（`NodeSearchEmbedding.process`）

```python
item_names = state.get("item_names")              # ['Birth Flower Cufflinks Gold Groom']
expr = f"item_name in {json_format(item_names)}"  # item_name in ["Birth Flower Cufflinks Gold Groom"]
reqs = get_search_reqs(..., expr=expr)
res = hybrid_search(collection_name=MilvusConfig.chunks_collection, reqs=reqs, ranker=(0.6, 0.4), ...)
```

用 `rewritten_query` 的向量在 chunks 表检索，`expr` 把范围限定在这 45 条里，结果只包含这款袖扣的内容，不会混进 Gold Dad 款或 Birthstone 款。

---

## 4. 为什么要分两步

如果直接拿大模型的名字：

- **精确过滤（`in`）**：差一个词就 0 条，见第 1 节。
- **不过滤、只靠向量**：同系列商品的说明书高度相似（各款袖扣的佩戴方法几乎一样），容易检索到别的款式，回答张冠李戴。

所以分成：

1. **模糊匹配**：在 item_name 表里用向量相似度，把"用户的叫法"映射成"库里的标准名"。
2. **精确过滤**：用标准名在 chunks 表里做字符串精确匹配。

item_name 表相当于一张"同义词 → 标准名"的映射表。

---

## 5. 前提和风险

1. **必须一字不差。** `in` 是字符串精确匹配，大小写、空格、破折号有一点不同就匹配不上。现在两边来自同一个变量，所以一致；以后如果只在一边加清洗逻辑（`.lower()`、`.strip()` 等），就会失配。
2. **重新导入要两张表一起更新。** 大模型每次识别结果可能不同。两个导入节点都先按 `file_title` 删除再插入，完整跑完时两边一致；但如果在 `NodeItemNameRecognition` 之后、`NodeImportMilvus` 之前失败，item_name 表已是新名字、chunks 表还是旧名字，这个商品就检索不到 chunk 了。
3. **多个 listing 共用一个名字。** 例如两个 listing 都叫 "Birth Flower Cufflinks Gold Plated"，过滤会把两边的 chunk 都取出来。同类商品通常可以接受；要精确到单个 listing，需要在对齐阶段带出 `file_title`，改用它过滤。
4. **阈值贴边。** 实测确认项 0.8510 只比 0.85 高 0.001，同系列其他款在 0.80 ~ 0.83，其他商品在 0.66 左右，自然分界约在 0.75。阈值需要用更多真实问题校准。
5. **转义只做一次。** `expr` 里的名字只靠 `json_format`（`json.dumps`）转义引号和反斜杠，不要再手动转义：两次转义会把 `"` 变成 `\\\"`，Milvus 解析成 `\"`，和库里的 `"` 对不上，一条都过滤不到。
