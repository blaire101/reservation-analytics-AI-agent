# Controlled SQL Analytics — Simplified

```text
LLM Structured Business Plan
  ↓
Stable IDs? → exact validation
Names?      → governed lookup only when needed
  ↓
Ambiguous?  → return candidate IDs; user retries with one ID
  ↓
Allowlisted metric / controlled SQL
  ↓
QueryBackend → Reservation Data Mart
```

The LLM interprets the request. Application code owns ID validation, name resolution, metric definitions, SQL templates, and output rules.
