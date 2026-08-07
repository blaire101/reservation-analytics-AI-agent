# Part 4 — Code Learning Path

This is the recommended order for understanding the code without jumping randomly between files.

## Stage 1 — Run first, read later

Run:

```bash
cp config/default.env .env
python scripts/run_demo.py
pytest -q
```

Goal: know what the application does before reading implementation details.

## Stage 2 — Understand the data

Read in this order:

1. `mock_data/dim_campaign.csv`
2. `mock_data/dm_reservation_conversion.csv`
3. `knowledge/reservation_analytics.md`

Goal: understand the campaign dimension, Reservation Data Mart grain, metrics, and business terminology.

## Stage 3 — Understand the request model

Read:

1. `app/schemas.py`
2. `app/services/extractor.py`
3. `app/prompts.py`

Goal: understand how natural language becomes structured business context.

## Stage 4 — Understand the workflow core

Read `app/graph.py` slowly.

Trace these decisions:

```text
extract
  ↓
classify / route
  ├─ knowledge
  └─ analytics
       ↓
     validate
       ↓
     resolve campaign
       ↓
     run analytics
```

This is the most important file in the project.

## Stage 5 — Understand the two branches

Knowledge branch:

1. `app/services/knowledge.py`
2. `knowledge/reservation_analytics.md`

Analytics branch:

1. `app/services/campaign_resolver.py`
2. `app/services/analytics.py`

Goal: be able to explain why RAG is not used to return live business counts.

## Stage 6 — Understand backend abstraction

Read:

1. `app/services/query_backend.py`
2. `app/services/backend_factory.py`
3. `app/services/sqlite_backend.py`
4. `app/services/athena.py`
5. `app/services/sql_gateway.py`

Goal: understand how one Analytics Tool can switch between local SQLite, AWS Athena, and an internal SQL Gateway.

## Stage 7 — Trace one request end to end

Use this example:

> How many users reserved Xiaomi 17 Pro in Germany for CMP001?

Trace it through:

```text
scripts/run_demo.py
→ agent_service.py
→ graph.py
→ extractor.py
→ campaign_resolver.py
→ analytics.py
→ backend_factory.py
→ sqlite_backend.py
→ local SQLite Data Mart
→ graph.py response
```

Then trace a knowledge question:

> What does reserved-but-not-ordered mean?

```text
agent_service.py
→ graph.py
→ knowledge.py
→ reservation_analytics.md
→ response
```

## Stage 8 — Only then read infrastructure integration

After the local flow is clear, read:

- `config/aws-athena.env`
- `config/internal-sg.env`
- `config/internal-eu.env`
- `existing_data_platform/`

This prevents cloud/platform details from hiding the core agent design.

## Target understanding

You have understood the project when you can explain these five points without looking at code:

1. Why there are two paths: knowledge and analytics.
2. Why `campaign_id` must be uniquely resolved before SQL runs.
3. Why the LLM does not own arbitrary SQL generation.
4. Why `QueryBackend` makes the AI layer independent from the data platform.
5. How Singapore and Europe can use different region/cluster configurations without changing the business workflow.
