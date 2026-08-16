# Multilingual Entity Resolution & Stateful Clarification

## Responsibility split

```text
extractor.py
    ↓ natural-language entities
repository.py
    ↓ governed candidates
resolver.py
    ↓ resolved / ambiguous / not_found
resolver.py
    ↓ final Campaign + Product + Country IDs
graph.py
    ↓ clarification memory when needed
service.py
    ↓ controlled analytics SQL
```

## Why this layer exists

Users do not always use warehouse-standard names. The application therefore separates semantic understanding from stable ID resolution.

```text
Natural-language question
        ↓
Structured Extraction
        ↓
Governed Dimension Candidates
  ├─ dim_site_df
  ├─ dim_product_df
  └─ dim_campaign_df
        ↓
Conservative Candidate Selection
   ├─ one clear match → stable ID
   ├─ multiple matches → clarification
   └─ no match → not_found
        ↓
Controlled Analytics SQL
```

## Product is optional input

A campaign row already owns `fproduct_id` and `fcountry_code`.

Therefore this request can be resolved:

```text
Germany + campaign name + reserved_users
```

The resolver uses country as an optional filter, resolves the campaign, then derives the final product and country IDs from the selected campaign row.

If the user also supplies product, product is resolved first and used to narrow campaign candidates.

## Safety rule

The LLM may compare user wording with governed candidates, but it may select only IDs returned from those dimensions. It does not invent `country_code`, `product_id`, or `campaign_id`.

## Clarification loop

When several candidates remain plausible, the API returns:

- `status = clarification`
- `pending_entity`
- governed candidate list
- the same `session_id`

The next message with the same `session_id` is treated as a clarification answer.

```text
Candidate ambiguity
   ↓
Ask user
   ↓
session_id memory
   ↓
User confirms
   ↓
resolver.confirm()
   ↓
normal resolver flow continues
   ↓
Stable IDs
```

The current project uses in-process Python memory. That is enough for a single-process demonstration and keeps the implementation easy to read.
