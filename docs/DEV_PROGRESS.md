# EtsyKnowledge 开发进展

## 基本约定

- **EtsyKnowledge 是唯一在开发的项目。** `~/PycharmProjects/knowledge_base` 已废弃，只当参考代码和文档看，不运行它的服务（import_service 8000 / query_service 8001）和 `upload_pdfs_sequential.py`。
- **数据只写入 Milvus 库 `etsy_kb`：**

  | 用途 | collection | 配置项（`.env`） |
  | --- | --- | --- |
  | 文档切片 + 向量 | `etsy_kb_chunks` | `CHUNKS_COLLECTION` |
  | 商品名 + 向量 | `etsy_kb_item_names` | `ITEM_NAME_COLLECTION` |

  库名由 `MILVUS_DB_NAME=etsy_kb` 指定，代码里统一通过 `knowledgebase/config/config.py` 的 `MilvusConfig` 读取。
- `default` 库里的 `kb_chunks` / `kb_item_names` 是 knowledge_base 留下的旧数据，与本项目无关。
- 中间件用本项目的 `docker-compose.yml`（`etsy-kb-*` 容器）。Attu：http://127.0.0.1:8080，连接地址填 `milvus:19530`，库选 `etsy_kb`。

## 导入流程进度

流程定义在 `knowledgebase/import_process/main_graph.py`（`MainGraphRunner`）：

entry → pdf_to_md → md_img → document_split → item_name_recognition → bge_embedding → import_milvus

| 节点 | 状态 |
| --- | --- |
| `node_entry` | 完成 |
| `node_pdf_to_md` | 完成 |
| `node_md_img` | 完成：图片上传 MinIO（按内容哈希存公共目录，同一张图只存一份）、生成图片摘要、改写 MD 图片链接 |
| `node_document_split` | 完成：按标题切分，过长的片段再递归切分 |
| `node_item_name_recognition` | 完成：识别商品名，写入 `etsy_kb_item_names`，并回填到每个 chunk |
| `node_bge_embedding` | 完成：BGE-M3 稠密 + 稀疏向量 |
| `node_import_milvus` | 完成：写入 `etsy_kb_chunks`（按 `file_title` 幂等删除后插入） |

网页上传：`knowledgebase/web/api/import_service.py`（端口 8000）+ `knowledgebase/web/page/import.html`，节点进度通过 `/status/{task_id}` 查询。

## 检索流程进度

流程定义在 `knowledgebase/query_process/main_graph.py`（`QueryMainGraphRunner`）：

item_name_confirm →（有 answer）→ answer_output；（无 answer）→ search_embedding / search_embedding_hyde / web_search_mcp → rrf → rerank → answer_output

| 节点 / 模块 | 状态 |
| --- | --- |
| `node_item_name_confirm` | 完成；名字完全一致时直接确认（Claude 修复，确认门槛 0.85 下完全相同的名字也只有约 0.835） |
| `node_search_embedding` / `node_search_embedding_hyde` / `node_web_search_mcp` | 完成 |
| `node_rrf` / `node_rerank` | 完成 |
| `node_answer_output` | 完成（Claude 代写，待自己重做） |
| `web/api/query_service.py`（端口 8001）+ `web/page/chat.html` | 完成（Claude 代写，待自己重做） |

Claude 代写的部分及与参考代码的差异见 [QUERY_SERVICE_CLAUDE_NOTES.md](QUERY_SERVICE_CLAUDE_NOTES.md)。

## 记录

- 2026-10-16：`node_item_name_recognition` 修复上下文传参（之前只传了最后一个 chunk）和空值判断；结果改为取 `res.content`。
- 2026-10-23：检索流程补上 `node_answer_output`、节点进度推送、`query_service.py` 和 `chat.html`（Claude 代写）。
- 2026-10-23：图片改为按内容哈希存 `upload-images/<哈希>.jpg`，旧数据（MinIO / Milvus 切片 / Mongo 历史）已迁移，详见 [QUERY_SERVICE_CLAUDE_NOTES.md](QUERY_SERVICE_CLAUDE_NOTES.md)。
