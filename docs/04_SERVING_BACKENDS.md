# Serving & Backends

FastAPI exposes:

```text
GET  /health
POST /ask
```

`POST /ask` needs only a natural-language `question`.

The analytics layer depends on one interface:

```python
backend.execute(sql)
```

Backends:
- local demo: SQLite
- AWS: remote query backend
- internal platform: SQL Gateway

The backend can change without changing LangGraph or metric logic.
