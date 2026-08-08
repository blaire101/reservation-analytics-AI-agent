# Reservation Analytics AI Agent

> A natural-language knowledge and analytics layer built on a trusted Reservation Data Mart.

- **LangGraph** controls routing and state.
- **LlamaIndex + FAISS** retrieve metric and data-model knowledge.
- **Structured Output** extracts Campaign + Product + Country context.
- **Controlled SQL** returns aggregate metrics or detail records.
- **FastAPI + Docker** serve and package the application.
- **SQLite** runs locally; Athena and SQL Gateway are optional adapters.

![End-to-End Architecture](docs/architecture/01-end-to-end.png)

## Start Here

1. Open `learning/reservation_ai_learning.html`.
2. Run notebooks `01` through `05`.
3. Read: `models.py → extractor.py → graph.py → rag.py → resolver.py → service.py → sqlite.py`.
4. Read remote backends only after the local path is clear.

## Four Parts

| Part | Purpose | Main files |
|---|---|---|
| **1 — Core AI** | Structured Output + LangGraph | `app/core/` |
| **2 — Knowledge RAG** | LlamaIndex + FAISS | `knowledge/`, `app/knowledge/rag.py` |
| **3 — SQL Analytics** | Context resolution + controlled SQL | `app/analytics/` |
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
  └── Analytics → Resolve Campaign + Product + Country
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
