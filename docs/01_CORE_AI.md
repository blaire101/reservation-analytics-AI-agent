# Part 1 — Core AI

![Core AI](architecture/02-core-ai.png)

## Goal

Understand how a natural-language request becomes structured business context and then moves through LangGraph.

## Read in This Order

```text
app/core/models.py
      ↓
app/core/extractor.py
      ↓
app/core/graph.py
```

## Concepts

- **Pydantic Structured Output** converts free text into `ReservationQuery`.
- **LangGraph State** stores the request as it moves between nodes.
- **Conditional edges** route Knowledge questions to RAG and Analytics questions to validation.
- Missing business context produces clarification instead of guessed values.

## Keep This Mental Model

```text
Question → Extract → Route
                    ├─ Knowledge
                    └─ Analytics
```

The graph does not contain SQL implementation or FAISS implementation. It only coordinates them.


## Stateful clarification

`ReservationAgent.invoke(question, session_id=...)` keeps clarification context for the session. When entity resolution is ambiguous, the state stores `pending_entity` and the governed candidate list. The user's next message is matched only against those candidates, then the workflow resumes with the confirmed stable ID. This is a lightweight prototype memory loop; a production deployment can replace the in-process store with durable checkpoint storage.
