# 导入数据存储位置

Milvus 和 MinIO 用的是 EtsyKnowledge 的 `etsy-kb-*` 容器（`docker-compose.yml`），数据文件落在 **`~/PycharmProjects/EtsyKnowledge/volumes/`** 下。开发进度见 `docs/DEV_PROGRESS.md`。

## 1. Milvus：文字切片和向量（检索时查这里）

- 容器：`etsy-kb-milvus`，地址 `127.0.0.1:19530`
- 数据库：`etsy_kb`（`.env` 里的 `MILVUS_DB_NAME`）
- 两个 collection：
  - `etsy_kb_chunks`：每份 PDF 切出来的文本块（含图片摘要），带 BGE-M3 向量和 `file_title` 等字段
  - `etsy_kb_item_names`：商品名索引，每份文件一条
- 磁盘位置：`~/PycharmProjects/EtsyKnowledge/volumes/milvus`
- 网页查看：Attu http://127.0.0.1:8080（连接地址填 `milvus:19530`，库选 `etsy_kb`）
- `default` 库里的 `kb_chunks` / `kb_item_names` 是已废弃的 knowledge_base 项目留下的，与本项目无关

## 2. MinIO：图片和原文件

- 容器：`etsy-kb-minio`，API `127.0.0.1:9000`，控制台 http://127.0.0.1:9001
- bucket `knowledge-base`：
  - `upload-images/`：PDF 里的图片。MD 和切片里的图片链接都指向这里，例如 `http://127.0.0.1:9000/knowledge-base/upload-images/011_…`
- 磁盘位置：`~/PycharmProjects/EtsyKnowledge/volumes/minio`

## 3. 配置

- 读的是 **`EtsyKnowledge/.env`**，代码通过 `knowledgebase/config/config.py` 读取
