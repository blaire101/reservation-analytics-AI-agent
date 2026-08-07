# End-to-End Architecture

This diagram shows the three boundaries that matter most:

1. **Request entry** — user, FastAPI, structured extraction, LangGraph.
2. **Two controlled answer paths** — LlamaIndex for knowledge; Analytics Tool for actual numbers.
3. **Data access** — a configurable SQL backend reads the trusted Reservation Data Mart.

The AI workflow is intentionally separated from the physical data platform.
