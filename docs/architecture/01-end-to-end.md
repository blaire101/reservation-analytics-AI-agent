# End-to-End Architecture — Simplified

```text
User / Feishu
  ↓
FastAPI
  ↓
LLM Structured Business Plan
  ↓
LangGraph Router
  ├─ Knowledge → RAG → FAISS → Grounded Answer
  └─ Analytics → Validate / Resolve → Controlled SQL → QueryBackend → Data Mart → Answer
```

Resolution rule:
- stable ID → exact validation
- natural-language name → resolve only when needed
- ambiguous → return governed choices; never guess
