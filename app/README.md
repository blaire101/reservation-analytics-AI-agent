# App Code Map

Read the project in this order:

```text
1. core/graph.py
   whole workflow

2. core/extractor.py
   question → typed request

3. analytics/resolver.py
   wording → governed context

4. analytics/matcher.py
   exact / partial / optional LLM match

5. analytics/repository.py
   dimension SQL

6. analytics/service.py
   controlled Data Mart SQL
```

## One important business rule

A campaign can contain multiple products.

Therefore:

```text
"CMP001 in Germany"
  → campaign-level analytics
  → all products in CMP001

"CMP001 + Mi 17 Pro in Germany"
  → product-level analytics
  → only P001
```

The resolver never forces one product when the user did not provide one.

## Entity resolution

```text
user wording
  ↓
governed candidates from dimensions
  ↓
exact match
  ↓
unique partial match
  ↓
optional LLM fallback
  ↓
ambiguous? ask the user
```

The LLM can only choose IDs returned by the dimension tables.

## Clarification loop

```text
first message
  → several candidates
  → save candidates under session_id

next message
  → resolver.confirm(...)
  → continue normal resolve(...)
  → controlled analytics SQL
```

Prototype session state is stored in Python process memory.
