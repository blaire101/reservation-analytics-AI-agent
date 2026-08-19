# Controlled SQL Analytics

The LLM produces a typed business plan, not SQL.

```text
metric + governed context
        ↓
allowlisted metric builder
        ↓
controlled SQL
        ↓
QueryBackend
        ↓
Reservation Data Mart
```

This makes the main safety boundary easy to explain: **LLM interprets language; application code controls SQL.**
