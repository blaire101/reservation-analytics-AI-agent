# Part 3 — Data Backends

## 1. One interface, multiple data platforms

![Configurable Data Backends](architecture/architecture-backends.png)

`AnalyticsService` depends on a `QueryBackend` interface instead of directly depending on Athena or an internal SQL engine.

```text
Analytics Tool
      ↓
QueryBackend
 ┌────┼──────────────┐
SQLite   Athena   Internal SQL Gateway
```

## 2. Default — SQLite

Purpose: make the complete project runnable on a laptop.

```env
DATA_BACKEND=sqlite
DATA_REGION=default
DATA_CLUSTER=local
```

At startup, sample `dim_campaign.csv` and `dm_reservation_conversion.csv` data are loaded into `local_data/reservation_analytics.db`.

## 3. AWS — Athena

```env
DATA_BACKEND=athena
AWS_REGION=ap-southeast-1
ATHENA_WORKGROUP=analytics
```

Typical production authentication is an **IAM role** attached to the runtime service. The Python AWS SDK resolves the role credentials; keys do not need to be hard-coded.

```text
Agent Service → AWS SDK → IAM → Athena → Glue Catalog → S3-backed Data Mart
```

## 4. Internal platform — SQL Gateway

```env
DATA_BACKEND=internal_sql_gateway
DATA_REGION=singapore
DATA_CLUSTER=sg-prod-01
SQL_GATEWAY_ENDPOINT=https://sql-gateway-sg.internal
SQL_GATEWAY_USER_ID=...
SQL_GATEWAY_TOKEN=...
SQL_GATEWAY_CATALOG=iceberg
```

Typical flow:

```text
Analytics Tool
    ↓
SQL Gateway Adapter
    ↓
user_id + token
    ↓
Regional SQL Gateway
    ↓
Trino / Presto / Hive
    ↓
Iceberg / Hive Reservation Data Mart
```

## 5. Region and cluster routing

![Region and Cluster Routing](architecture/architecture-regions.png)

European and Singapore workloads can use different gateways, clusters, catalogs, and credentials. The region/cluster choice is configuration and routing logic, not business metric logic.

Example:

```text
country = DE → europe → eu-prod-01
country = SG → singapore → sg-prod-01
```

This separation keeps the AI workflow portable while preserving data-residency and platform boundaries.
