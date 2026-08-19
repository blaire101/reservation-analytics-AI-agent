# Serving and Data Backends

FastAPI serves the agent. `QueryBackend` keeps SQLite, remote query backend, and SQL Gateway separate from agent logic.

```text
config/local.env     → SQLite
config/aws.env       → remote query backend
config/internal.env  → SQL Gateway
```

Changing backend configuration does not change LangGraph, RAG, or analytics metric logic. Secrets are loaded from the root `.env` file.
