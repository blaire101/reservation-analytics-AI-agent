# Core AI

The LLM has one simple job: convert natural language into a typed **business plan**.

```text
question → intent + metric + business fields
```

LangGraph then routes the plan:

```text
extract → knowledge
       ↘ validate → resolve → analytics
```

Important boundary: **LLM interprets language; application code controls IDs and SQL.**
