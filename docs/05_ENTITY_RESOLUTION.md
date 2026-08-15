# Multilingual Entity Resolution & Stateful Clarification

## Why this layer exists

Operations users do not always use warehouse-standard names. They may write in English, Chinese, mixed language, abbreviations, or informal campaign wording.

The application therefore separates **semantic understanding** from **stable ID resolution**.

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

## Safety rule

The LLM may compare the user's wording with governed candidates, but it may select only IDs returned from those dimensions. It does not invent `country_code`, `product_id`, or `campaign_id`.

## Clarification loop

When several candidates remain plausible, the API returns:

- `status = clarification`
- `pending_entity`
- the governed candidate list
- the same `session_id`

The next message with the same `session_id` is treated as the user's confirmation. The agent keeps the previous metric and already-resolved context, then resumes entity resolution and analytics.

```text
Candidate ambiguity
   ↓
Ask user
   ↓
session_id memory
   ↓
User confirms
   ↓
Resume resolver
   ↓
Stable IDs
```

The project discussion prototype uses in-process session memory. For multiple production pods, use a durable checkpoint store such as Redis or a database-backed LangGraph checkpoint implementation.
