# Part 3 — SQL Analytics

![Controlled SQL Analytics](architecture/04-sql-analytics.png)

## Goal

Return aggregate metrics or detail records through controlled SQL.

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
Structured Business Context
↓
Validate Required Fields
↓
Resolve Campaign + Product + Country
↓
Choose Controlled SQL
↓
backend.execute(sql)
↓
dm_reservation_subject_df
↓
Metric or Detail Result
```

## Resolution Rule

- 0 matches → return not found.
- 1 match → execute analytics SQL.
- Multiple matches → ask for clarification.

Detail responses return `fuser_id_hash`; raw `fuser_id` is not exposed. The LLM does not generate unrestricted production SQL.
