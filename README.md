# EtsyKnowledge

掌柜智库 × CedarSeaGoods（Etsy 店铺）知识库。把店铺的商品资料（PDF / Markdown）解析、切片、向量化后写入 Milvus，供后续的客服问答检索使用。

## 导入流程

基于 LangGraph 的 `StateGraph`，每个节点是一个继承 `NodeBase` 的类（`knowledgebase/import_process/`）：

```
START → node_entry ─┬─ PDF → node_pdf_to_md → node_md_img
                    ├─ MD  ──────────────────→ node_md_img
                    └─ 其他 → END

node_md_img → node_document_split → node_item_name_recognition
            → node_bge_embedding → node_import_milvus → END
```

| 节点 | 作用 |
| --- | --- |
| `node_entry` | 校验输入文件，按后缀设置 `is_pdf_read_enabled` / `is_md_read_enabled` |
| `node_pdf_to_md` | PDF 结构化解析为 Markdown（MinerU） |
| `node_md_img` | 处理 Markdown 中的图片（上传 MinIO） |
| `node_document_split` | 文档切片 |
| `node_item_name_recognition` | 识别商品名称 |
| `node_bge_embedding` | BGE-M3 生成向量 |
| `node_import_milvus` | 写入 Milvus |

所有节点共享的状态字段定义在 `state.py` 的 `ImportGraphState`。

> 目前只有 `node_entry` 已实现，其余节点仍是占位。

## 目录

```
knowledgebase/
  import_process/   导入流程：base.py、state.py、main_graph.py、nodes/
  tool/logger.py    彩色日志
  test/             学习 / 实验脚本
docker-compose.yml  Milvus + etcd + MinIO + Neo4j + MongoDB + Attu
```

`metadata/`、`data/`、`volumes/` 含店铺数据和本地运行数据，已在 `.gitignore` 中排除，不在仓库里。

## 环境

需要 Python 3.11 和 [uv](https://docs.astral.sh/uv/)。

```bash
uv sync                      # 创建 .venv 并安装依赖
cp .env.example .env         # 填入 API key、模型路径等
docker compose up -d         # 启动基础设施
```

在 VS Code / PyCharm 里把解释器设为 `.venv/bin/python`。

本项目的端口与课程默认端口错开，可与其他知识库项目同时运行：

| 服务 | 宿主机端口 |
| --- | --- |
| MinIO API / 控制台 | 9100 / 9101 |
| Milvus / 健康检查 | 19540 / 9191 |
| Neo4j HTTP / Bolt | 7475 / 7688 |
| MongoDB | 27018 |
| Attu（Milvus 管理界面） | 8081 |

## 运行

在项目根目录执行（输入路径是相对根目录的）：

```bash
uv run python -m knowledgebase.import_process.main_graph
```

## License

MIT
