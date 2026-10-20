# EtsyKnowledge

Knowledge base for CedarSeaGoods (an Etsy shop). It parses, chunks and embeds the shop's product documents (PDF / Markdown) and writes them into Milvus, then answers customer-service questions by retrieving from them.

Both pipelines are built on LangGraph's `StateGraph`; each node is a class that inherits from `NodeBase`.

## Import pipeline

`knowledgebase/import_process/`

```
START → node_entry ─┬─ PDF → node_pdf_to_md → node_md_img
                    ├─ MD  ──────────────────→ node_md_img
                    └─ other → END

node_md_img → node_document_split → node_item_name_recognition
            → node_bge_embedding → node_import_milvus → END
```

| Node | Purpose |
| --- | --- |
| `node_entry` | Validates the input file and sets `is_pdf_read_enabled` / `is_md_read_enabled` based on the file extension |
| `node_pdf_to_md` | Parses PDF into structured Markdown (MinerU) |
| `node_md_img` | Processes images in the Markdown (uploads them to MinIO) |
| `node_document_split` | Splits the document into chunks |
| `node_item_name_recognition` | Recognizes the product name with an LLM (from the listing title, falling back to the first chunks), stores it in the item-name collection and writes it back to every chunk |
| `node_bge_embedding` | Generates dense + sparse embeddings with BGE-M3 (the product name is prepended to each chunk's content) |
| `node_import_milvus` | Writes the chunks to Milvus |

Both Milvus writes delete existing rows by `file_title` first, so re-importing a file is idempotent. Shared state fields are defined in `ImportGraphState` (`import_process/state.py`).

## Query pipeline

`knowledgebase/query_process/`

```
START → node_item_name_confirm ─┬─ product not confirmed → node_answer_output
                                └─ confirmed → node_search_embedding      ─┐
                                               node_search_embedding_hyde ─┼→ node_rrf → node_rerank → node_answer_output → END
                                               node_web_search_mcp        ─┘
```

| Node | Purpose |
| --- | --- |
| `node_item_name_confirm` | Uses the chat history (MongoDB) and the question to extract product names and a rewritten query, then aligns them to the stored product names via hybrid search on the item-name collection. Score ≥ 0.85 confirms a name; 0.6–0.85 asks the customer to choose; otherwise asks them to rephrase |
| `node_search_embedding` | Hybrid search on the chunks with the rewritten query, filtered by `item_name in [confirmed names]` |
| `node_search_embedding_hyde` | HyDE: the LLM writes a hypothetical answer, and the query + answer are searched with the same filter |
| `node_web_search_mcp` | Web search via MCP (Tavily), keeping only English guide pages (no marketplaces, social sites or product pages) |
| `node_rrf` | Reciprocal Rank Fusion of the two local result lists (web results join at rerank) |
| `node_rerank` | Cross-encoder rerank — **TODO** |
| `node_answer_output` | Answer generation — **TODO** |

Shared state fields are defined in `QueryGraphState` (`query_process/state.py`). See [docs/ITEM_NAME_FLOW.md](docs/ITEM_NAME_FLOW.md) for how `item_name` connects the two pipelines.

## Layout

```
knowledgebase/
  config/           config.py (settings from .env), prompt.py (LLM prompts)
  import_process/   Import pipeline: base.py, state.py, main_graph.py, batch_import.py, nodes/
  query_process/    Query pipeline: base.py, state.py, main_graph.py, nodes/
  tool/             Milvus, MinIO and MongoDB clients, BGE-M3 download, JSON formatting, colored logging
  utils/            BGE-M3 embedding helpers
  test/             Learning / experiment scripts
docs/               Design notes and progress log
docker-compose.yml  Milvus + etcd + MinIO + Neo4j + MongoDB + Attu
```

`metadata/`, `data/` and `volumes/` contain shop data and local runtime data. They are excluded in `.gitignore` and are not in the repository.

## Setup

Requires Python 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                      # create .venv and install dependencies
cp .env.example .env         # fill in API keys, model paths, etc.
docker compose up -d         # start the infrastructure
```

In VS Code / PyCharm, set the interpreter to `.venv/bin/python`.

| Service | Host port |
| --- | --- |
| MinIO API / console | 9000 / 9001 |
| Milvus / health check | 19530 / 9091 |
| Neo4j HTTP / Bolt | 7475 / 7688 |
| MongoDB | 27018 |
| Attu (Milvus admin UI) | 8080 |

Data is written to the `etsy_kb_chunks` and `etsy_kb_item_names` collections in the Milvus database `etsy_kb`; see `docs/DATA_STORAGE.md` and `docs/DEV_PROGRESS.md` for details.

## Run

Run from the project root (input paths are relative to the root).

Import a single file:

```bash
uv run python -m knowledgebase.import_process.main_graph
```

Batch import every PDF under `metadata/CedarSeaGoods_KB/pdf` (already imported files are skipped):

```bash
uv run python -m knowledgebase.import_process.batch_import --workers 3
# --only 06_pet-gifts   only import paths containing this string
# --limit N             import at most N files
# --force               re-import everything
```

Each query node can be run on its own with sample state, e.g.:

```bash
uv run python -m knowledgebase.query_process.nodes.node_item_name_confirm
```

## License

MIT
