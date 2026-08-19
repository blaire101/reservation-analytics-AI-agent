# Entity Resolution — Simplified Quick Review Version

The resolver follows one easy rule:

```text
Stable ID supplied → exact dimension-table validation → continue
Natural-language name → lookup governed dimensions → one match continue / many matches clarify
```

Examples:

- `CMP001` → validate `fcampaign_id = 'CMP001'`; do not ask the LLM to choose it again.
- `Germany` → resolve to `DE` from `dim_site_df`.
- `Phone Mi 17 Pro` → resolve to `P001` from `dim_product_df`.

If multiple governed candidates remain, the service returns their IDs and asks the user to retry with one ID. The simple demo deliberately avoids a session-memory confirmation loop.
