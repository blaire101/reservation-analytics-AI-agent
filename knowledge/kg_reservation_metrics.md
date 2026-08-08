# Knowledge — Reservation Metrics

This document defines the main business terms and metrics used by the Reservation Analytics AI Agent.

## 1. Reservation

A reservation means a user expressed purchase intent for a product within a specific campaign and country/site.

The analytics context is:

```text
User × Campaign × Product × Country
```

---

## 2. Reserved User

A **Reserved User** is a user with:

```text
freserve_flag = 1
```

Typical metric:

```text
COUNT(DISTINCT fuser_id)
```

---

## 3. Ordered User

An **Ordered User** is a reserved user who later placed an order:

```text
freserve_flag = 1
AND
forder_flag = 1
```

Typical metric:

```text
COUNT(DISTINCT fuser_id)
```

---

## 4. Reserved but Not Ordered

A **Reserved-but-not-ordered User** reserved during the campaign but did not later place an order.

Business condition:

```text
freserve_flag = 1
AND
forder_flag = 0
```

The Data Mart also provides:

```text
ftag_reserved_not_paid = 1
```

In this project, the business meaning of this field is **reserved but not ordered**.

---

## 5. Reservation-to-Order Conversion Rate

Formula:

```text
Ordered Users / Reserved Users
```

Example:

```text
Reserved Users = 100
Ordered Users  = 62

Conversion Rate = 62 / 100 = 62%
```

The denominator must be reserved users in the same Campaign + Product + Country context.

---

## 6. Campaign Context

Natural-language analytics questions should resolve to an unambiguous:

```text
Campaign + Product + Country
```

before analytics SQL runs.

Example:

```text
Phone Mi 17 Pro
+ Germany
+ August launch
```

may resolve to:

```text
fcampaign_id  = CMP001
fproduct_id   = P001
fcountry_code = DE
```

If no matching context exists, return not found.

If multiple contexts match, ask for clarification instead of guessing.

---

## 7. Aggregate and Detail Queries

The analytics path supports both:

```text
Aggregate metrics
+
Detail records
```

Examples of aggregate questions:

```text
How many users reserved?
How many users ordered?
What is the conversion rate?
```

Example of a detail question:

```text
Show the users who reserved but did not order.
```

For detail-level results:

```text
fuser_id_hash
```

may be returned.

Raw:

```text
fuser_id
```

must not be exposed in the agent response.

---

## 8. Data Source

Business metrics and detail records are queried from:

```text
dm_reservation_subject_df
```

Supporting context is resolved with:

```text
dim_campaign_df
dim_product_df
dim_site_df
dim_category_df
```

The RAG path explains definitions and data-model knowledge.

The SQL analytics path returns actual metrics or detail records.
