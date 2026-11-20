# AWS Architecture — Cloud Infrastructure Metrics & Log Analytics Pipeline

## Overview

This document describes how the local SQLite pipeline maps to a production-grade AWS architecture using managed services.

```
                        ┌─────────────────────────────────────────────────────────────────┐
                        │                    AWS Cloud  (eu-west-1)                        │
                        │                                                                   │
  ┌──────────────┐      │  ┌───────────────────────────────────────────────────────────┐   │
  │  Data Sources│      │  │                    S3 DATA LAKE                           │   │
  │              │      │  │                                                           │   │
  │  sales.csv   │─────▶│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
  │  events.csv  │      │  │  │  raw/       │  │  silver/    │  │  gold/          │  │   │
  │  users.csv   │      │  │  │  (Bronze)   │  │  (Parquet)  │  │  (Parquet)      │  │   │
  │  marketing   │      │  │  │             │  │  stg_users  │  │  agg_channel_   │  │   │
  └──────────────┘      │  │  │  users.csv  │  │  stg_orders │  │  kpis           │  │   │
                        │  │  │  sales.csv  │  │  stg_events │  │  fct_orders     │  │   │
                        │  │  │  events.csv │  │  stg_market.│  │  fct_events     │  │   │
                        │  │  │  marketing  │  │             │  │  dim_users      │  │   │
                        │  │  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │   │
                        │  └─────────┼────────────────┼──────────────────┼───────────┘   │
                        │            │                 │                  │               │
                        │  ┌─────────▼─────────────────▼──────────────────▼───────────┐  │
                        │  │                   AWS GLUE                                │  │
                        │  │                                                           │  │
                        │  │  ┌─────────────┐   ┌─────────────────────────────────┐   │  │
                        │  │  │  Crawlers   │   │       glue_job.py (ETL)         │   │  │
                        │  │  │             │   │                                  │   │  │
                        │  │  │  bronze_    │   │  Bronze → Silver (clean/type)   │   │  │
                        │  │  │  silver_    │   │  Silver → Gold  (aggregate)     │   │  │
                        │  │  │  gold_      │   │  Glue 3.0 / G.1X Workers       │   │  │
                        │  │  └─────────────┘   └─────────────────────────────────┘   │  │
                        │  │                                                           │  │
                        │  │  ┌─────────────────────────────────────────────────────┐  │  │
                        │  │  │              GLUE DATA CATALOG                      │  │  │
                        │  │  │  bronze_users │ stg_orders │ agg_channel_kpis …    │  │  │
                        │  │  └─────────────────────────────────────────────────────┘  │  │
                        │  └───────────────────────────────────────────────────────────┘  │
                        │                              │                                   │
                        │  ┌───────────────────────────▼───────────────────────────────┐  │
                        │  │                      AMAZON ATHENA                         │  │
                        │  │         Standard SQL queries on S3 Parquet files           │  │
                        │  │         Workgroup: cloud-metrics-dev                       │  │
                        │  │         Results: s3://…-athena-results/results/            │  │
                        │  └───────────────────────────────────────────────────────────┘  │
                        │                              │                                   │
                        │  ┌───────────────────────────▼───────────────────────────────┐  │
                        │  │                   AMAZON QUICKSIGHT                        │  │
                        │  │   Connects to Athena → Interactive dashboards              │  │
                        │  │   CVR · LTV · CAC · ROAS · Funnel · Cohort · RFM          │  │
                        │  └───────────────────────────────────────────────────────────┘  │
                        └─────────────────────────────────────────────────────────────────┘
```

---

## Service Mapping: Local → AWS

| Local Component | AWS Equivalent | Purpose |
|---|---|---|
| `data/raw/*.csv` | **S3** `raw/` prefix | Raw data landing zone (Bronze) |
| `etl/ingest.py` | **S3 Upload** + **Glue Crawler** | Auto-discover schema, populate Glue Catalog |
| `etl/transform.py` | **AWS Glue** `glue_job.py` | PySpark Bronze→Silver→Gold transforms |
| `data/analytics.db` | **S3** `gold/` Parquet + **Athena** | Serverless SQL query layer |
| `sql/analytics/*.sql` | **Athena** Named Queries | Same SQL, runs on S3 Parquet |
| `dashboard/kpi_dashboard.py` | **Amazon QuickSight** | Managed BI — connects to Athena |
| Manual `python pipeline.py` | **Amazon EventBridge** (cron) | Pipeline scheduling |
| `tests/test_pipeline.py` | **AWS CodePipeline** + **pytest** | CI/CD + data quality checks |

---

## Cost Estimate (dev workload, ~145K rows)

| Service | Usage | Est. Monthly Cost |
|---|---|---|
| S3 (5 GB) | Storage + requests | ~$0.15 |
| Glue (crawlers + job) | 1 run/day × 5 min × G.1X | ~$3.00 |
| Athena | 1 GB scanned/month | ~$0.005 |
| QuickSight (1 author) | Standard tier | ~$18.00 |
| **Total** | | **~$21/month** |

---

## Deploy Steps

### Prerequisites
- AWS CLI configured: `aws configure`
- Python 3.9+, Terraform ≥ 1.6 (optional)

### Option A — CloudFormation

```bash
# 1. Upload Glue script to S3 first (create a temp bucket manually)
aws s3 cp aws/glue_job.py s3://MY-SCRIPTS-BUCKET/scripts/glue_job.py

# 2. Deploy the stack
aws cloudformation deploy \
  --template-file aws/cloudformation.yaml \
  --stack-name cloud-metrics-dev \
  --parameter-overrides \
      ProjectName=cloud-metrics \
      Environment=dev \
      GlueJobScriptPath=s3://MY-SCRIPTS-BUCKET/scripts/glue_job.py \
  --capabilities CAPABILITY_IAM
```

### Option B — Terraform

```bash
cd aws/terraform

# 1. Initialise providers
terraform init

# 2. Preview changes
terraform plan -var="environment=dev"

# 3. Apply
terraform apply -var="environment=dev"
```

### Step 3 — Upload raw data to S3

```bash
# Get bucket name from outputs
BUCKET=$(aws cloudformation describe-stacks \
  --stack-name cloud-metrics-dev \
  --query "Stacks[0].Outputs[?OutputKey=='DataLakeBucket'].OutputValue" \
  --output text)

# Upload raw data
aws s3 cp data/raw/ s3://$BUCKET/raw/ --recursive
```

### Step 4 — Run Glue Crawler then ETL Job

```bash
# Start bronze crawler
aws glue start-crawler --name cloud-metrics-dev-bronze-crawler

# Wait for it to finish, then run the ETL job
aws glue start-job-run --job-name cloud-metrics-dev-etl-job
```

### Step 5 — Query with Athena

```sql
-- In the AWS Console → Athena → Workgroup: cloud-metrics-dev
SELECT channel, total_revenue, avg_roas
FROM cloud_metrics_dev.agg_channel_kpis
ORDER BY total_revenue DESC;
```

---

## QuickSight → Athena Connection

1. Go to **QuickSight Console** → New Dataset
2. Choose **Athena**
3. Select workgroup: `cloud-metrics-dev`
4. Select database: `cloud_metrics_dev`
5. Choose table: `agg_channel_kpis` (or any gold table)
6. Build dashboards with the same KPIs: **CVR, LTV, CAC, ROAS, Funnel, RFM**

---

## Security Best Practices Applied

- ✅ S3 server-side encryption (AES-256)
- ✅ S3 bucket versioning enabled
- ✅ Athena query results automatically deleted after 7 days
- ✅ IAM least-privilege: Glue role only has access to its own S3 buckets
- ✅ Query cost guardrail: 10 GB max scan per Athena query
- ✅ Glue job bookmarks to avoid reprocessing old data
- ✅ Intelligent tiering lifecycle policy (S3 costs reduced after 30 days)
