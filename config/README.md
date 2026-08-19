# Configuration

The project keeps environment behavior separate from secrets.

## Files

| File | Purpose |
|---|---|
| `local.env` | Default SQLite learning mode |
| `aws.env` | remote query backend |
| `internal.env` | Internal SQL Gateway backend |

## Common Keys

```text
APP_ENV
DATA_BACKEND
KNOWLEDGE_DIR
DATA_REGION
DATA_CLUSTER
DATA_DATABASE
LLM_ENABLED
OPENAI_MODEL
OPENAI_EMBEDDING_MODEL
```

Backend-specific keys:

```text
SQLite:      SQLITE_PATH
Remote query backend: provider-specific settings
SQL Gateway: SQL_GATEWAY_ENDPOINT
```

## Secrets

Do not place real secrets in `config/*.env`.

Create a root `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Typical secrets:

```text
OPENAI_API_KEY
SQL_GATEWAY_USER_ID
SQL_GATEWAY_TOKEN
```

The loader reads the selected `config/*.env` file first, then `.env`, and finally applies process environment variables as the highest-priority values.

## Examples

```python
load_settings("config/local.env")
load_settings("config/aws.env")
load_settings("config/internal.env")
```

To switch the internal route from Singapore to Europe, edit only:

```text
DATA_REGION=eu
DATA_CLUSTER=eu-prod
SQL_GATEWAY_ENDPOINT=https://sql-gateway-eu.example.internal/query
```

## Multilingual Entity Resolution

Cross-language semantic matching (for example `德国` → governed candidate `DE — Germany`) requires `OPENAI_API_KEY configured` and a runtime `OPENAI_API_KEY`.

The resolver still remains controlled: it first loads candidates from `dim_site_df`, `dim_product_df`, or `dim_campaign_df`, and the LLM may only select IDs from that candidate set. Offline/local fallback uses conservative lexical matching and asks for clarification instead of guessing when it cannot safely resolve an entity.
