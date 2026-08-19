# Application structure

The code is split for code readability, while each module stays intentionally small.

```text
app/
├── rag/          # knowledge ingestion, embedding, FAISS, retrieval
├── analytics/    # validation, ID/name resolution, metrics, query backend
├── graph/        # LangGraph state, nodes, workflow
├── api/          # FastAPI request / response layer
├── llm/          # shared structured LLM client
├── settings.py
└── main.py
```

## Core rule

- LLM: understands the user's intent and produces a typed **business plan**.
- Stable ID (`CMP001`, `P001`, `DE`): **exact validation**, no semantic search.
- Natural-language name (`Mi 17 Pro`, `Germany`): resolve only when needed.
- Application code: owns the allowlisted metrics and controlled SQL.
- Ambiguous request: return candidate IDs and ask the user to retry; no session-resume loop in this simple demo.
