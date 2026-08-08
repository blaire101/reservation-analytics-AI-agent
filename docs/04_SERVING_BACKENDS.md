# Part 4 — Serving and Data Backends

![Serving and Data Backends](architecture/05-data-backends.png)

## Goal

Keep serving and physical data access separate from the Core AI workflow.

## FastAPI

`app/main.py` exposes two small endpoints:

```text
GET  /health
POST /ask
```

## Docker

The Dockerfile packages Python, FastAPI, LangGraph, LlamaIndex, FAISS, and the analytics code into one runnable service.

## Backend Contract

The upper analytics layer only needs:

```python
backend.execute(sql)
```

Implementations:

```text
SQLiteBackend      → local default
AthenaBackend      → AWS SDK + IAM
SQLGatewayBackend  → endpoint + user_id + token
```

Region and cluster values are configuration only. They do not change the agent workflow.
