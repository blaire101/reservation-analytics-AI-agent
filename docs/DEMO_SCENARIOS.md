# Demo Scenarios

## 1. Knowledge question

**Question**

What does reserved-but-not-ordered mean?

**Expected route**

```text
Extract → Knowledge → LlamaIndex
```

## 2. Metric knowledge

**Question**

How is reservation-to-order conversion rate calculated?

**Expected route**

```text
Extract → Knowledge → LlamaIndex
```

## 3. Exact analytics

**Question**

How many users reserved Xiaomi 17 Pro in Germany for CMP001 but did not order?

**Expected route**

```text
Extract
→ Validate
→ Campaign Resolver
→ CMP001
→ Analytics Tool
→ Athena / mock DM
```

Mock result: **3 users**.

## 4. Missing context

**Question**

How many users reserved Xiaomi 17 Pro?

**Expected result**

The agent asks for country/site and campaign.

## 5. Ambiguous campaign

**Question**

Analyze the Xiaomi 17 Pro campaign in Germany in August 2026.

Mock dimension returns:

- CMP001 — Xiaomi 17 Pro Launch
- CMP002 — Back-to-School Campaign
- CMP003 — Mi Fan Campaign

The agent asks the user to choose.

Follow-up:

`CMP001`

The previous context is merged with this choice.

Mock summary:

- Reserved Users: 8
- Ordered Users: 5
- Reserved-but-not-ordered Users: 3
- Conversion Rate: 62.50%
