# App Code Map — Slim Version

## Main flow

```text
User
  ↓
extractor.py
  LLM → typed request
  ↓
graph.py
  route workflow
  ↓
resolver.py
  dimensions → governed IDs
  ↓
service.py
  controlled SQL
  ↓
Reservation Data Mart
```

Knowledge questions branch from `graph.py` to `knowledge/rag.py`.

## Read only these four files first

1. `core/graph.py` — whole workflow
2. `core/extractor.py` — LLM structured extraction
3. `analytics/resolver.py` — entity resolution + clarification
4. `analytics/service.py` — controlled Data Mart SQL

Then, only if needed:

- `analytics/repository.py` = dimension SQL
- `core/session.py` = `{session_id: pending state}`
- `core/models.py` = typed contracts

## Multi-turn clarification

```text
resolver finds several candidates
    ↓
return clarification
    ↓
graph saves candidates by session_id
    ↓
user replies "1" or "CMP001"
    ↓
resolver.confirm()
    ↓
continue resolve()
    ↓
analytics
```

## LLM policy

The LLM is a required dependency.

There is no second keyword/offline implementation.
If the LLM is unavailable, `/ask` returns `status="unavailable"` clearly.

The LLM understands language, but it may only select entity IDs returned by
governed dimension tables. Controlled analytics SQL remains application code.

## Multi-product campaign rule

A campaign can contain multiple products.

- Campaign only → aggregate all products.
- Campaign + product → add `product_id` as a filter.
