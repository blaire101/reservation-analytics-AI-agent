# Part 1 — Project Overview

## 1. Business problem

A reservation event happens before product launch. The useful downstream questions are not only *who reserved*, but whether that user later ordered and which campaign/product/site context produced the conversion.

The Reservation Data Mart is the trusted analytics layer. Its grain is:

> **User × Campaign × Product × Site**

The AI application is a new consumption layer on top of this trusted model; it does not redesign the Data Mart.

## 2. Data foundation

```text
Reservation / Order facts + Campaign / Product / Site dimensions
                         ↓
                  Reservation Data Mart
                         ↓
                   SQL query engine
```

Depending on the environment, the SQL query engine can be SQLite, Athena, or an internal SQL Gateway backed by Trino/Presto/Hive/Iceberg.

## 3. AI application

![End-to-End Architecture](architecture/architecture-overview.png)

The application has two controlled answer paths:

1. **Knowledge path** — business definitions and metric logic from LlamaIndex RAG.
2. **Analytics path** — validated business context, a uniquely resolved `campaign_id`, and controlled SQL against the Data Mart.

## 4. Core business fields

| Field | Meaning |
|---|---|
| `user_id` | User identifier |
| `campaign_id` | Unique campaign identifier |
| `product_id` | Reserved product SKU |
| `site` | Site / market context |
| `reserve_flag` | 1 = user reserved |
| `order_flag` | 1 = user ordered |
| `tag_reserved_not_paid` | Existing field name; business meaning here is reserved but not ordered |
| `channel` | Traffic / acquisition channel |

## 5. Why the Data Mart matters

The AI layer should query a stable business model instead of rebuilding joins from raw tables for every question. This keeps metric logic reusable, governed, and easier to test.
