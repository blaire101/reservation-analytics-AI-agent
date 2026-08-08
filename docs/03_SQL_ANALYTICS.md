# Part 3 — SQL Analytics

![Controlled SQL Analytics](architecture/04-sql-analytics.png)

## Goal

Return actual business numbers while keeping campaign selection and SQL execution controlled by application code.

## Read in This Order

```text
app/analytics/resolver.py
      ↓
app/analytics/service.py
      ↓
app/data/sqlite.py
```

## Flow

```text
Business Context
↓
Validate Required Fields
↓
Resolve one campaign_id
↓
Choose an allowlisted metric SQL template
↓
backend.execute(sql)
↓
Reservation Data Mart
```

## Campaign Rule

- 0 matches → return not found.
- 1 match → execute analytics SQL.
- Multiple matches → ask for one `campaign_id`.

The LLM does not generate unrestricted production SQL.
