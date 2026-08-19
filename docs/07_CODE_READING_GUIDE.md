# Code Reading Guide

The main Python files are intentionally written in a **learning-friendly style**.
Important functions include:

- a detailed docstring explaining purpose, inputs, outputs, and flow;
- short inline comments before important steps;
- explicit separation between LLM interpretation and deterministic application logic.

## Recommended reading order

```text
1. app/graph/workflow.py
        ↓
2. app/graph/nodes/extract.py
        ↓
3. app/rag/service.py
        ↓
4. app/rag/ingestion/loader.py
        ↓
5. app/rag/embeddings/embedder.py
        ↓
6. app/rag/vectorstore/faiss_store.py
        ↓
7. app/rag/retrieval/retriever.py
        ↓
8. app/analytics/validation/validator.py
        ↓
9. app/analytics/resolution/service.py
        ↓
10. app/analytics/resolution/repository.py
        ↓
11. app/analytics/metrics/reservation.py
        ↓
12. app/analytics/service.py
        ↓
13. app/analytics/query/backend.py
        ↓
14. app/api/routes.py
```

## One sentence to remember

> The LLM understands the business intent; application code controls routing, entity validation, SQL, and the final trusted data path.
