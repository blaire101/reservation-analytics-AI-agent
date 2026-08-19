# Code Walkthrough

Read these packages in order:

1. `app/graph/workflow.py` — the whole flow on one page.
2. `app/graph/nodes/extract.py` — LLM → typed business plan.
3. `app/analytics/validation/validator.py` — lightweight validation.
4. `app/analytics/resolution/` — stable ID exact check; name lookup only when needed.
5. `app/analytics/metrics/` — allowlisted business metric SQL.
6. `app/analytics/service.py` — execute and format the result.
7. `app/rag/` — loading, embedding, FAISS, retrieval.
8. `app/api/` — thin FastAPI interface.

The modules are deliberately small so each one is easy to explain step by step.
