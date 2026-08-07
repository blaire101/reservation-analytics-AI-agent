# Reservation Analytics AI Agent

A small AI / Agent layer built on top of a **configurable Reservation Data Mart**.

The key design is that **AI orchestration is decoupled from the data platform**.
The same Analytics Tool can use a local SQL Data Mart, AWS Athena, or an internal
SQL gateway for Hive / Iceberg / Trino-style platforms.

## Architecture

```text
Reservation + Order + Dimensions
        ↓
DWD facts + DIM context
        ↓
Reservation Data Mart
        ↓
Queryable data platform
(SQLite / Athena / Internal SQL Gateway)
        ↓

Operations User
        ↓
FastAPI
        ↓
Structured Extraction + Validation
        ↓
LangGraph
     ↙          ↘
Knowledge      Analytics
   ↓              ↓
LlamaIndex    Campaign Resolver
   ↓              ↓
Knowledge     dim_campaign
                  ↓
             campaign_id
                  ↓
            Analytics Tool
                  ↓
            QueryBackend
                  ↓
           Reservation DM
```

Core grain: **User × Campaign × Product × Site**

Business flow: **Reservation → Order**

## Design principle

> RAG is for knowledge. SQL is for data.

The LLM never writes unrestricted SQL. Structured business context is validated,
a unique campaign is resolved, and the application executes controlled SQL
queries.

## Default mode — real local SQL, no AWS required

The default configuration is:

```text
MOCK_MODE=true
DATA_BACKEND=sqlite
DATA_REGION=default
DATA_CLUSTER=local
```

`MOCK_MODE=true` means no OpenAI key is needed for extraction / knowledge answers.
It does **not** mean analytics numbers are hard-coded. The project creates a real
SQLite database from the sample DIM and DM CSVs and executes SQL against it.

```bash
cd AWS-Reservation-Analytics-AI-Agent-26
python scripts/run_demo.py
```

Expected CMP001 data:

```text
8 reserved
5 ordered
3 reserved-but-not-ordered
62.50% conversion
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

## API

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "ops-001",
    "message": "What was the conversion rate for Xiaomi 17 Pro in Germany for CMP001?"
  }'
```

## Switch to AWS Athena

`.env`:

```text
DATA_BACKEND=athena
AWS_REGION=ap-southeast-1
ATHENA_WORKGROUP=analytics
ATHENA_OUTPUT=s3://your-athena-results/
```

Use IAM role / AWS SDK credential chain for authentication.

## Switch to an internal data platform

`.env`:

```text
DATA_BACKEND=internal_sql_gateway
DATA_REGION=europe
DATA_CLUSTER=eu-prod-01
SQL_GATEWAY_ENDPOINT=https://sql-gateway.internal/query
SQL_GATEWAY_USER_ID=...
SQL_GATEWAY_TOKEN=...
SQL_GATEWAY_CATALOG=iceberg
```

The exact SQL-gateway request/response contract is company-specific; the included
adapter is a clean example boundary for interview discussion.

## Real LlamaIndex + LLM mode

The AI mode is independent of the SQL backend. You can keep SQLite while turning
on the real LLM/RAG path:

```text
MOCK_MODE=false
DATA_BACKEND=sqlite
OPENAI_API_KEY=...
```

That gives:

```text
Real structured extraction + LlamaIndex RAG
                    ↓
            LangGraph routing
                    ↓
       Analytics Tool → local SQLite DM
```

This is useful for demonstrating the complete AI workflow without needing AWS.

See `docs/DATA_BACKENDS.md` for backend and region/cluster configuration.


## Backend configuration examples

Ready-to-copy examples are under `config/`:

```text
config/default.env       # local SQLite, default runnable mode
config/aws-athena.env    # AWS / IAM / Athena
config/internal-eu.env   # EU cluster + SQL gateway + token/user identity
config/internal-sg.env   # Singapore cluster + SQL gateway + token/user identity
```
