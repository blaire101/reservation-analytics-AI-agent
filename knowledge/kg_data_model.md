# Knowledge — Data Model

This document describes the core warehouse tables used by the Reservation Analytics AI Agent.

## Naming Convention

- `dim_*_df`: daily full-snapshot dimension table.
- `dm_*_df`: daily full-snapshot Data Mart table.
- `fdate`: partition field.
- `fetl_time`: ETL processing time.
- All columns start with `f`.
- Column types use only `STRING` and `BIGINT`.
- Every table includes `fcreate_time` and `fmodify_time`.

---

## 1. `dm_reservation_subject_df`

**Grain:** User × Campaign × Product × Country.

| Field | Type | Description |
|---|---|---|
| `fdate` | STRING | Partition field |
| `fetl_time` | STRING | ETL processing time |
| `fid` | BIGINT | Technical row ID |
| `fuser_id` | STRING | Internal raw user identifier |
| `fuser_id_hash` | STRING | Hashed user identifier used in analytics outputs and detail responses |
| `fcampaign_id` | STRING | Campaign ID |
| `fproduct_id` | STRING | Product ID |
| `fcountry_code` | STRING | Country/site code, Business site / market code, e.g. SG, TW, HK, DE |
| `freserve_flag` | BIGINT | `1=Reserved, 0=Not reserved` |
| `forder_flag` | BIGINT | `1=Ordered, 0=Not ordered` |
| `ftag_reserved_not_paid` | BIGINT | `1=Reserved but not ordered, 0=Otherwise` |
| `freservation_time` | STRING | Reservation time |
| `forder_time` | STRING | Order time |
| `fcreate_time` | STRING | Source record creation time |
| `fmodify_time` | STRING | Source record modification time |

### Sample

| fuser_id | fuser_id_hash | fcampaign_id | fproduct_id | fcountry_code | freserve_flag | forder_flag |
|---|---|---|---|---|---:|---:|
| `U001` | `HASH_U001` | `CMP001` | `P001` | `DE` | 1 | 1 |
| `U002` | `HASH_U002` | `CMP001` | `P001` | `DE` | 1 | 0 |
| `U003` | `HASH_U003` | `CMP002` | `P001` | `SG` | 1 | 0 |

**Output rule:** detail-level analytics should return `fuser_id_hash`, not raw `fuser_id`.

---

## 2. `dim_campaign_df`

**Grain:** one row per Campaign × Product × Country instance.

| Field | Type | Description |
|---|---|---|
| `fdate` | STRING | Partition field |
| `fetl_time` | STRING | ETL processing time |
| `fid` | BIGINT | Source-system technical ID |
| `fcampaign_id` | STRING | Campaign business ID |
| `fcampaign_group_id` | STRING | Optional parent / global campaign ID |
| `fcampaign_name` | STRING | Campaign name |
| `fcampaign_type` | STRING | Campaign type |
| `fproduct_id` | STRING | Product ID |
| `fcountry_code` | STRING | Country/site code, Business site / market code, e.g. SG, TW, HK, DE |
| `fstart_time` | STRING | Campaign start time |
| `fend_time` | STRING | Campaign end time |
| `fcampaign_status` | BIGINT | `0=Planned, 1=Active, 2=Ended` |
| `fcreate_time` | STRING | Source record creation time |
| `fmodify_time` | STRING | Source record modification time |

### Sample

| fcampaign_id | fcampaign_group_id | fcampaign_name | fproduct_id | fcountry_code | fcampaign_status |
|---|---|---|---|---|---:|
| `CMP001` | `CG001` | Phone Mi 17 Pro Launch | `P001` | `DE` | 2 |
| `CMP002` | `CG001` | Phone Mi 17 Pro Launch | `P001` | `SG` | 2 |

---

## 3. `dim_product_df`

**Grain:** one row per product.

| Field | Type | Description |
|---|---|---|
| `fdate` | STRING | Partition field |
| `fetl_time` | STRING | ETL processing time |
| `fid` | BIGINT | Source-system technical ID |
| `fproduct_id` | STRING | Product business ID |
| `fproduct_name` | STRING | Product name |
| `fcategory_lv1_id` | STRING | Level-1 category ID |
| `fcategory_lv2_id` | STRING | Level-2 category ID |
| `fcategory_lv3_id` | STRING | Level-3 category ID |
| `fis_active` | BIGINT | `1=Active, 0=Inactive` |
| `fcreate_time` | STRING | Source record creation time |
| `fmodify_time` | STRING | Source record modification time |

### Sample

| fproduct_id | fproduct_name | fcategory_lv1_id | fcategory_lv2_id | fcategory_lv3_id |
|---|---|---|---|---|
| `P001` | Phone Mi 17 Pro | `C01` | `C0101` | `C010101` |

---

## 4. `dim_category_df`

**Grain:** one row per level-3 category path.

| Field | Type | Description |
|---|---|---|
| `fdate` | STRING | Partition field |
| `fetl_time` | STRING | ETL processing time |
| `fid` | BIGINT | Source-system technical ID |
| `fcategory_lv1_id` | STRING | Level-1 category ID |
| `fcategory_lv1_name` | STRING | Level-1 category name |
| `fcategory_lv2_id` | STRING | Level-2 category ID |
| `fcategory_lv2_name` | STRING | Level-2 category name |
| `fcategory_lv3_id` | STRING | Level-3 category ID |
| `fcategory_lv3_name` | STRING | Level-3 category name |
| `fcreate_time` | STRING | Source record creation time |
| `fmodify_time` | STRING | Source record modification time |

### Sample

| fcategory_lv1_name | fcategory_lv2_name | fcategory_lv3_name |
|---|---|---|
| Electronics | Mobile Devices | Smartphones |

---

## 5. `dim_site_df`

**Grain:** one row per country/site.

| Field | Type | Description |
|---|---|---|
| `fdate` | STRING | Partition field |
| `fetl_time` | STRING | ETL processing time |
| `fid` | BIGINT | Source-system technical ID |
| `fcountry_code` | STRING | Country/site code, Business site / market code, e.g. SG, TW, HK, DE |
| `fcountry_name` | STRING | Country/site name |
| `fregion_code` | STRING | Business region code |
| `fregion_name` | STRING | Business region name |
| `fcurrency_code` | STRING | Currency code |
| `ftimezone` | STRING | Time zone |
| `fis_active` | BIGINT | `1=Active, 0=Inactive` |
| `fcreate_time` | STRING | Source record creation time |
| `fmodify_time` | STRING | Source record modification time |

### Sample

| fcountry_code | fcountry_name | fregion_code | fregion_name |
|---|---|---|---|
| `SG` | Singapore | `SEA` | Southeast Asia |
| `DE` | Germany | `WEU` | Western Europe |

---

## Relationship Summary

```text
dim_product_df ───────┐
                      │
dim_campaign_df ──────┼──→ dm_reservation_subject_df
                      │
dim_site_df ──────────┘

dim_product_df
    │
    └── category IDs ──→ dim_category_df
```

The analytics path resolves an unambiguous:

```text
Campaign + Product + Country
```

before running analytics SQL against `dm_reservation_subject_df`.

Detail-level results return `fuser_id_hash`; raw `fuser_id` is not exposed.
