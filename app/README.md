# Application Code Map

The application is intentionally split by responsibility so each file answers one question.

```text
app/
├── main.py                    # HTTP API only
├── settings.py                # Configuration only
├── core/
│   ├── models.py              # Shared Pydantic / state models
│   ├── extractor.py           # Question -> typed request
│   ├── validation.py          # Is there enough campaign context?
│   ├── session.py             # In-process clarification state
│   └── graph.py               # LangGraph orchestration
├── analytics/
│   ├── repository.py          # Read governed dimension candidates
│   ├── selector.py            # Match user wording to candidates
│   ├── resolver.py            # Country -> Product(optional) -> Campaign
│   ├── service.py             # Controlled analytics SQL
│   └── sql_utils.py           # Small SQL helper
├── knowledge/
│   └── rag.py                 # LlamaIndex + FAISS knowledge path
└── data/
    ├── backend.py             # QueryBackend interface + factory
    ├── sqlite.py              # Local implementation
    └── remote.py              # Athena / SQL Gateway implementations
```

## Read the project in this order

### 1. Main business flow

Read only these first:

```text
core/graph.py
  -> core/extractor.py
  -> analytics/resolver.py
  -> analytics/service.py
```

That is enough to explain the end-to-end behavior.

### 2. Understand entity resolution

Then read:

```text
analytics/repository.py
  -> analytics/selector.py
```

- `repository.py` answers: **where do candidate IDs come from?**
- `selector.py` answers: **how do we choose one candidate safely?**
- `resolver.py` answers: **what order do we resolve business context in?**

### 3. Understand session memory

Read:

```text
core/session.py
```

It stores only pending clarification state by `session_id`.

## Analytics resolution flow

```text
ReservationQuery
      ↓
Resolve country if supplied
      ↓
Resolve product if supplied
      ↓
Query campaign candidates
      ↓
Unique campaign?
  ├─ yes -> load Campaign
  └─ no  -> clarification
              ↓
         session memory
              ↓
         user confirms
              ↓
         resolver continues
      ↓
Campaign supplies final:
country_code + product_id + campaign_id
      ↓
AnalyticsService
      ↓
Data Mart
```

A user does **not** have to provide product when the campaign can determine it uniquely.
