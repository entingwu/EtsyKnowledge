# 检索服务：Claude 代写部分（待自己重新补做）

2026-10-23 由 Claude 参考以下代码写成，用来先把检索流程和聊天页面跑通。以后要自己重新写一遍时，按本文的清单逐项替换即可。

- 参考仓库：https://gitee.com/ly03171629/kb_0515/tree/master/atguigu （主要照这个写）
- 对照：`~/PycharmProjects/knowledge_base/atguigu`（只读参考，没有运行）
- 课程文档：`20【掌柜智库】【检索】API和前端页面.md`、`21【掌柜智库】【检索】答案输出.md`

## 改动清单

| # | 文件 | 类型 | 内容 |
| --- | --- | --- | --- |
| 1 | `knowledgebase/config/prompt.py` | 追加 | `ANSWER_PROMPT`（英文） |
| 2 | `knowledgebase/tool/mongo_tool.py` | 修改 | `save_chat_message` 增加 `image_urls` 参数，新增和修改都写入该字段 |
| 3 | `knowledgebase/query_process/state.py` | 修改 | `QueryGraphState` 增加 `task_id` |
| 4 | `knowledgebase/query_process/base.py` | 修改 | `NodeBase.__call__` 上报节点状态、耗时，并 `put_data` 推送 `progress` 事件 |
| 5 | `knowledgebase/query_process/nodes/node_answer_output.py` | 重写 | 原来是 TODO 空壳 |
| 6 | `knowledgebase/web/api/query_service.py` | 新建 | 检索 API，端口 8001 |
| 7 | `knowledgebase/web/page/chat.html` | 新建 | 从参考仓库复制；界面文字改成英文（欢迎语、示例问题换成店里商品），图片区块正则加上 `[Images]` |
| 8 | `knowledgebase/query_process/nodes/node_item_name_confirm.py` | 修改 | `align_item_names`：名字完全一致（忽略大小写和多余空格）就直接确认，新增 `normalize_item_name` |
| 9 | `knowledgebase/tool/task_utils.py` | 修改 | 节点展示名改成英文：`_NODE_NAME_TO_CN` → `_NODE_NAME_TO_DISPLAY`，`_to_cn` → `_to_display`（导入页面也会显示英文节点名） |
| 10 | `node_answer_output.py` + `chat.html` | 修改 | 图片按文件名（内容哈希）去重，不再按完整 URL 去重 |
| 11 | `knowledgebase/import_process/nodes/node_md_img.py` | 修改 | 图片改存公共目录 `upload-images/<哈希>.jpg`，已存在就跳过上传；去掉按 listing 目录的幂等性删除（共用图片可能还被别的 listing 引用）。新增 `object_exists` |

## 各部分说明

### 1. `ANSWER_PROMPT`

结构和参考一致：【参考内容】【历史对话】【相关商品】【用户问题】+ 图片区块规则。与参考的不同：

- 改成英文，和本地其他 prompt 保持一致；多加一条"用和顾客问题相同的语言回答"。
- 图片区块的标记改成英文 `[Images]`，`chat.html` 里识别图片区块的正则也同步改成 `/【\s*图片\s*】|\[\s*(图片|Images?)\s*\]/gi`（旧的 `【图片】` 仍然能识别）。

### 4. `query_process/base.py`

照导入流程 `import_process/base.py` 的写法：执行前 `add_running_task`，执行后 `add_done_task` + `add_node_duration`；每次状态变化都 `put_data(task_id, "progress", get_task_info(task_id))`。

注意：`put_data` 在队列不存在时会 `sleep` 等待，所以**直接运行 `main_graph.py` 前必须先 `create_queue(task_id)`**，否则会卡住。

### 3. `state.py` 加 `task_id`

LangGraph 会丢弃 state schema 里没有声明的 key，不加的话节点里 `state.get("task_id")` 拿到的是 `None`。

### 5. `node_answer_output.py`

`process` 两条分支：

- `state["answer"]` 已有（意图确认阶段已给出反问或抱歉）：直接推 `final` 事件 `{"answer": answer}`。这条历史记录在 `node_item_name_confirm` 里已经写过了，这里不重复写。
- 没有 answer：依次调用下面四个方法。

| 方法 | 作用 |
| --- | --- |
| `format_prompt` | 拼接 `reranked_docs`（`[序号][source][title][url]` + 正文）、历史对话、`item_names`、`rewritten_query`，截断到 12000 字 |
| `generate_answer` | `init_chat_model(...).stream()`，每段推 `delta` 事件 `{"delta": ...}`，同时拼出完整答案 |
| `get_image_urls` | 正则 `!\[.*?\]\((.*?)\)` 从 chunk 正文提取图片，去重并保持顺序 |
| `write_history` | 写入 MongoDB（role=assistant，带 `image_urls`、`item_names`、`rewritten_query`），再推 `final` 事件 `{"image_urls": [...]}` |

与参考的不同：

- 模型用 `LLMConfig.llm_default_model` 和 `llm_default_temperature`（和本地 `node_item_name_confirm` 一致），参考用的是 `item_model`、温度 0。
- `get_recent_messages` 返回的是按时间倒序的记录，所以拼历史时先 `reversed`。
- 图片去重时保持原顺序（参考用 `list(set)`，顺序是乱的），并且按文件名去重：013 和 015 两个同名 listing 有 11 张相同的照片，文件名一样（内容哈希），但上传在 MinIO 的不同目录下，按 URL 去重会显示两次。`chat.html` 会把答案 `[Images]` 区块、`final` 的 `image_urls` 和文本里的链接合在一起显示，所以前端也要按文件名去重。

### 6. `query_service.py`（端口 8001）

| 接口 | 说明 |
| --- | --- |
| `POST /query` | body `{"query", "session_id"}`；先 `create_queue(task_id)`，再起后台任务 `run_main_graph`，返回 `task_id` |
| `GET /stream/{task_id}` | SSE，从队列取事件，按 `event: xxx\ndata: {...}\n\n` 输出 |
| `GET /history/{session_id}?limit=50` | 按时间正序返回，带 `image_urls`（`chat.html` 加载历史时会用它显示图片） |
| `DELETE /history/{session_id}` | 清空会话 |
| `GET /health` | `{"ok": true}` |

`run_main_graph`：开始和结束各推一次 `progress`；出错时推 `error` 事件 `{"error": ..., 状态信息}`。

与参考的不同：

- 队列在 `/query` 里创建（参考仓库在后台任务里创建，课程文档在 `/query` 里），这样 `/stream` 一连上就有队列。
- SSE 生成器收到 `final` 或 `error` 后就 `break`。参考是 `while True` 死循环，前端关闭连接后线程会一直阻塞在 `q.get()` 上。

## 测试方法

```bash
# 启动（项目根目录）
.venv/bin/python -m knowledgebase.web.api.query_service
# 打开页面
open knowledgebase/web/page/chat.html
```

2026-10-23 的测试结果：

- 服务链路：`/query` → `/stream` 能收到 `progress` 和 `final`，`/history` 和 `DELETE /history` 正常。
- 答案输出：手动给定 `item_names` 后，检索 → RRF → 重排 → 答案输出跑通，拿到 7 篇文档，51 段 `delta`，答案带图片区块，`final` 里有 5 张图片，MongoDB 历史里也有 `image_urls`。

## 已知问题

- ~~意图确认几乎永远在反问~~（已修，见改动 8）：确认门槛是 `score >= 0.85`，但混合检索（dense 0.8 + sparse 0.2）下，完全相同的商品名得分也只有约 0.835。现在名字完全一致就直接确认；名字不完全一致时仍然走 0.85 / 0.6 的门槛。
- **答案里会出现外部网站链接。** 测试时模型把网络搜索结果里的 hobbylobby.com 链接放进了 `[Images]` 区块，prompt 的"图片只能来自本地切片"约束不够。`knowledge_base` 里的 `_sanitize_urls` 是用代码删掉不在参考内容里的链接，可以参考。
- **只发商品名时，问题会被改写成别的问题。** 只发 "Velvet Ruffle Christmas Tree Skirt" 时，`rewritten_query` 被改写成了运费问题，答案也在讲运费。
- 同名商品：`Velvet Ruffle Christmas Tree Skirt` 对应两个 listing（013 和 015），检索时两个 listing 的切片会混在一起。

## 图片存储迁移（2026-10-23，一次性）

原来每个 listing 的图片存在 `upload-images/<file_title>/` 下面，同一张照片被多个 listing 用到时会存好几份，URL 也不同，回答里就会出现重复的图（1674 张里有 16 份重复，涉及 6 个 listing，其中 013/015 两个同名 listing 共用 11 张）。改动 11 之后，又用一次性脚本迁移了旧数据：

1. MinIO：1658 张不重复的图片复制到 `upload-images/<哈希>.jpg`，删除了旧的 listing 子目录。
2. Milvus `etsy_kb_chunks`：1674 个切片正文里的图片 URL 改成新路径。集合是 auto_id，所以是重新插入新行，再删除旧行；向量沿用原来的，没有重新计算。迁移前后总数都是 6871。
3. MongoDB：2 条聊天记录的 `text` / `image_urls` 一起改了。
4. 验证：1658 个图片 URL 全部 HTTP 200，检索返回的图片都是新路径。

没有改的：`output/` 下的本地中间文件（`*_new.md`、`chunks.json`）里还是旧 URL，只影响查看，不影响检索。
