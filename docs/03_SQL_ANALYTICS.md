# Controlled SQL Analytics

The analytics path separates natural-language understanding from trusted execution.

```text
Question
  ↓
Structured ReservationQuery
  ↓
Validate required context
  ↓
Dimension-backed entity resolution
  ├─ dim_site_df     → country_code
  ├─ dim_product_df  → product_id
  └─ dim_campaign_df → campaign_id
  ↓
Unique?
  ├─ yes → Stable IDs
  └─ no  → Clarification → session memory → resume
  ↓
AnalyticsService
  ↓
QueryBackend.execute(sql)
  ↓
dm_reservation_subject_df
```

The candidate selector is conservative: it may compare multilingual or informal user wording against dimension candidates, but it can only return IDs that came from those governed dimensions. It never invents warehouse IDs.

`AnalyticsService` still owns supported metrics and SQL templates. The LLM does not get unrestricted database access.
