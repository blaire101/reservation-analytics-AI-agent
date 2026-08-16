# Reservation Analytics AI Agent

> A natural-language knowledge and analytics layer built on a trusted Reservation Data Mart.

- **LangGraph** controls routing and state.
- **LlamaIndex + FAISS** retrieve metric and data-model knowledge.
- **Structured Output** classifies Knowledge vs Analytics and extracts multilingual business context.
- **Dimension-backed Entity Resolution** maps free-text country/product/campaign mentions to governed candidates and stable IDs.
- **Stateful Clarification** keeps candidate context by `session_id` and resumes after the user confirms an ambiguous entity.
- **Controlled SQL** returns aggregate metrics or detail records.
- **FastAPI + Docker** serve and package the application.
- **SQLite** runs locally; Athena and SQL Gateway are optional adapters.

![End-to-End Architecture](docs/architecture/01-end-to-end.png)

## Start Here

1. Open `presentation/reservation_ai_learning_v837.html`.
2. Run notebooks `01` through `05`.
3. Read `app/README.md`, then follow the short code-reading path there.
4. Read remote backends only after the local path is clear.

## Four Parts

| Part | Purpose | Main files |
|---|---|---|
| **1 — Core AI** | Structured Output + LangGraph | `app/core/` |
| **2 — Knowledge RAG** | LlamaIndex + FAISS | `knowledge/`, `app/knowledge/rag.py` |
| **3 — SQL Analytics** | Candidate lookup + entity resolution + controlled SQL | `app/analytics/` |
| **4 — Serving & Backends** | FastAPI, Docker, backend adapters | `app/main.py`, `app/data/` |

## Knowledge Sources

```text
knowledge/
├── kg_data_model.md
└── kg_reservation_metrics.md
```

LlamaIndex loads every Markdown file in this folder.

## Local Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add secrets only when needed
python run.py
pytest -q
```

Run the API:

```bash
uvicorn app.main:app --reload
```

## Core Flow

```text
Question
  ↓
Structured Output
  ↓
LangGraph
  ├── Knowledge → LlamaIndex → FAISS → Grounded Answer
  └── Analytics → Validate → Dimension Candidates
                              ↓
                    Conservative Entity Match
                      ↙ unique      ambiguous ↘
                 Stable IDs        Clarify User
                      ↑                 ↓
                      └──── session memory ────┘
                              ↓
                         Controlled SQL
                               ↓
                         QueryBackend
                               ↓
                  dm_reservation_subject_df
```

The analytics path supports aggregate metrics and detail records. Detail responses return `fuser_id_hash`; raw `fuser_id` is not exposed.

## Data Model

Core Data Mart:

```text
dm_reservation_subject_df
Grain: User × Campaign × Product × Country
```

Supporting dimensions:

```text
dim_campaign_df
dim_product_df
dim_category_df
dim_site_df
```

See `knowledge/kg_data_model.md` for the exact schema.

## Backend Switching

The analytics layer only calls:

```python
backend.execute(sql)
```

```text
config/local.env     → SQLite
config/aws.env       → Athena
config/internal.env  → SQL Gateway; edit region/cluster/endpoint only
```

See `config/README.md` for the common keys, backend-specific keys, and secret-loading rules.


## Multilingual Entity Resolution & Clarification

The LLM does **not** invent `DE`, `P001`, or `CMP001`. It extracts the user's wording, then the application queries governed dimensions and allows selection only from returned candidate IDs.

```text
"Germany" / "德国"
        ↓
dim_site_df candidates
        ↓
DE

"Mi 17" / "M Brand17" / irregular spacing
        ↓
dim_product_df candidates
        ↓
unique product_id OR clarification

campaign description
        ↓
dim_campaign_df candidates (already narrowed by product/country/time)
        ↓
unique campaign_id OR clarification
```

**Product is optional input.** If a campaign is uniquely identified, the campaign dimension supplies its product and country IDs.

If multiple candidates remain, `/ask` returns `status=clarification`, `pending_entity`, and governed candidates. The next message with the same `session_id` is treated as the user's confirmation and resumes resolution before analytics SQL runs.

```json
{
  "question": "Use CMP001",
  "session_id": "chat_001:thread_009:user_888"
}
```

For a generic API client, `session_id` is optional. If omitted, `/ask` generates and returns one; reuse that returned ID for any clarification follow-up. For Feishu, the adapter should derive a stable key from chat + thread/root message + user so concurrent users do not share state.

The bundled implementation uses lightweight in-process Python session memory for the project discussion prototype. It survives only while that process is alive. This is intentional for the demo; durable cross-process or multi-pod state is an optional production evolution.
