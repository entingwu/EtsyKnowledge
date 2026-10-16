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
| `node_md_img` | 完成：图片上传 MinIO、生成图片摘要、改写 MD 图片链接 |
| `node_document_split` | 完成：按标题切分，过长的片段再递归切分 |
| `node_item_name_recognition` | 进行中：已能用 LLM 识别商品名；还没做向量化写入 `etsy_kb_item_names`，也还没把商品名回填到每个 chunk |
| `node_bge_embedding` | 未开始（空壳）；`utils/embedding_utils.py` 已有 BGE-M3 稠密 + 稀疏向量工具 |
| `node_import_milvus` | 未开始（空壳），写入 `etsy_kb_chunks` |

`etsy_kb` 目前还是空的，等上面三个节点完成后，再批量导入 `metadata/CedarSeaGoods_KB/pdf` 下的 140 份 PDF。

## 记录

- 2026-10-16：`node_item_name_recognition` 修复上下文传参（之前只传了最后一个 chunk）和空值判断；结果改为取 `res.content`。
