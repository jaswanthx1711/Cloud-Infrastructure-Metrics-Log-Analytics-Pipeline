# 🎤 Interview Presentation Guide
## Cloud Infrastructure Metrics & Log Analytics Pipeline

> **Use this document to confidently explain your project in any data engineering, analytics, or cloud interview.**

---

## 📌 Table of Contents

1. [30-Second Elevator Pitch](#-30-second-elevator-pitch)
2. [What Does This Project Actually Do?](#-what-does-this-project-actually-do)
3. [Architecture Deep Dive](#-architecture-deep-dive)
4. [Tech Stack Explained](#-tech-stack-explained)
5. [ETL Pipeline Walkthrough](#-etl-pipeline-walkthrough)
6. [Analytical Capabilities](#-analytical-capabilities)
7. [Dashboard & Visualisation](#-dashboard--visualisation)
8. [AWS Cloud Design](#-aws-cloud-design)
9. [KPIs — Know These Cold](#-kpis--know-these-cold)
10. [Common Interview Questions & Answers](#-common-interview-questions--answers)
11. [Role-Specific Angles](#-role-specific-angles)
12. [Metrics to Quote](#-metrics-to-quote)

---

## ⚡ 30-Second Elevator Pitch

> *"I built an end-to-end data analytics pipeline that ingests raw business data — sales transactions, user clickstream events, and marketing campaign data — and transforms it into clean, queryable layers. The pipeline runs analytical SQL queries on top to compute business KPIs like Conversion Rate, Customer Lifetime Value, Customer Acquisition Cost, and ROAS, then surfaces all of that in an interactive Streamlit dashboard with 5 pages of charts and filters. The architecture mirrors a real-world production setup: locally it uses Python + SQLite, and the design has a full AWS equivalent using S3, Glue, Athena, and QuickSight — with Infrastructure as Code via CloudFormation and Terraform."*

---

## 🔍 What Does This Project Actually Do?

This is a **repeatable ETL (Extract → Transform → Load) analytics pipeline** for cloud infrastructure metrics. Think of it like a mini data warehouse built from scratch.

### The Business Problem It Solves

Imagine a SaaS company that:
- Has **5,000 users** spread across 6 acquisition channels (organic, paid, social, email, referral, direct)
- Runs **20 marketing campaigns** with real spend budgets
- Processes **8,000 sales orders** across 50 products
- Receives **60,000 user behaviour events** (clicks, page views, cart additions)

**The challenge:** All this data sits in separate CSV files. Business stakeholders can't answer questions like:
- "Which marketing channel gives us the best return on spend?"
- "Where in the funnel are we losing customers?"
- "Which customer segments should we re-target?"

**This pipeline answers all of that automatically.**

### The Three-Layer Data Architecture

```
Raw CSVs  →  Bronze (raw)  →  Silver (cleaned)  →  Gold (aggregated)  →  Dashboard
```

| Layer | What It Contains | Purpose |
|---|---|---|
| **Bronze** | Exact copy of raw CSVs in database | Audit trail, data lineage |
| **Silver** | Cleaned, typed, deduplicated staging tables | Ready for analysis |
| **Gold** | Pre-computed KPIs, fact tables, dimension tables | Fast dashboard queries |

---

## 🏗 Architecture Deep Dive

### Local / Development Architecture

```
data/raw/*.csv
   ↓ (etl/ingest.py)
Bronze Layer — SQLite (raw_users, raw_sales, raw_user_events, raw_marketing)
   ↓ (etl/transform.py)
Silver Layer — stg_users, stg_events, stg_sales, stg_marketing
   ↓ (etl/transform.py continued)
Gold Layer  — dim_users, dim_products, fct_orders, fct_events, agg_channel_kpis
   ↓ (etl/pipeline.py analytics queries)
Processed CSVs — funnel_conversion, cohort_retention, rfm_segmentation …
   ↓ (dashboard/kpi_dashboard.py)
Streamlit Dashboard — 5 interactive pages
```

### AWS / Production Architecture

```
S3 raw/               → Glue Crawler  → Glue Data Catalog
S3 silver/ + gold/    ← Glue ETL Job  ← glue_job.py (PySpark)
Athena (SQL on S3)    → QuickSight    → Interactive Business Dashboards
EventBridge (cron)    → Scheduled pipeline runs
CloudFormation / Terraform → Infrastructure as Code
```

---

## 🛠 Tech Stack Explained

| Component | Local Tool | AWS Equivalent | Why This Choice |
|---|---|---|---|
| **Data Storage** | SQLite | S3 + Parquet | SQLite = zero-config for dev; Parquet = columnar, compressed, cost-efficient at scale |
| **ETL Engine** | Python + Pandas | AWS Glue (PySpark) | Pandas perfect for <1M rows locally; Glue scales to terabytes |
| **SQL / Querying** | SQLite SQL | Amazon Athena | Serverless, pay-per-query; no cluster management |
| **Dashboard** | Streamlit + Plotly | Amazon QuickSight | Streamlit = fast prototyping; QuickSight = managed, enterprise-ready |
| **Scheduling** | Manual (`python pipeline.py`) | Amazon EventBridge | Cron-based scheduled triggers |
| **IaC** | — | CloudFormation + Terraform | Two options provided; Terraform for multi-cloud portability |
| **Testing** | Pytest | AWS CodePipeline | 13 unit tests covering data quality and transformations |
| **BI Export** | CSV + Excel + Tableau .tds | — | Tableau Data Source + Power BI connection guide included |

---

## ⚙️ ETL Pipeline Walkthrough

The master orchestrator is `etl/pipeline.py`. It runs in 4 steps:

### Step 1 — Data Generation (if no raw data present)
```
etl/generate_data.py → Creates realistic synthetic data using Faker + NumPy
```
- **5,000 users** with channels, countries, age groups, subscription plans
- **60,000 user events** simulating funnel drop-off (visit → product_view → cart → checkout → purchase)
- **8,000 sales orders** with pricing, discounts, statuses (85% completed, 10% returned, 5% cancelled)
- **20 marketing campaigns** with spend, impressions, clicks, conversions

**Key design decision:** Funnel events use realistic drop-off probabilities:
```
visit (100%) → product_view (65%) → add_to_cart (40%) → checkout (22%) → purchase (12%)
```

### Step 2 — Bronze Ingestion
```
etl/ingest.py → Loads CSVs into SQLite as raw_* tables (no transformations)
```
- Preserves raw data as-is for audit and lineage purposes
- Tables: `raw_users`, `raw_user_events`, `raw_sales`, `raw_marketing`

### Step 3 — Silver + Gold Transformations
```
etl/transform.py → 9 transformation steps
```

**Silver (cleaning + typing):**
- `stg_users` — deduplicate on user_id, normalise email, add plan_rank
- `stg_events` — parse timestamps, extract date/week/month, add stage_order
- `stg_sales` — compute net_revenue (price × qty × (1 - discount%)), add month/quarter
- `stg_marketing` — compute CTR, CVR, CAC, ROAS per campaign

**Gold (business aggregations):**
- `dim_users` — user dimension table
- `dim_products` — product + category dimension
- `fct_orders` — orders fact table joined with user attributes
- `fct_events` — events fact table joined with user attributes
- `agg_channel_kpis` — pre-aggregated channel performance (joins sales + marketing)

### Step 4 — Analytics Export
6 analytical SQL queries run and export to `data/processed/*.csv`:
- `funnel_conversion.csv` — stage-by-stage conversion rates
- `cohort_retention.csv` — weekly cohort retention matrix
- `monthly_revenue.csv` — revenue by month and channel
- `channel_kpis.csv` — CAC, ROAS, LTV, CVR per channel
- `product_performance.csv` — top 20 products by revenue
- `rfm_segmentation.csv` — users scored by Recency, Frequency, Monetary value

---

## 📊 Analytical Capabilities

### 1. Funnel Analysis
Tracks user drop-off at each stage of the purchase journey.

**Business Question answered:** "Where exactly are we losing customers?"

```sql
SELECT stage, COUNT(DISTINCT user_id) AS users,
       100.0 * COUNT(DISTINCT user_id) / MAX(COUNT(...)) OVER () AS pct_of_top
FROM fct_events
GROUP BY stage ORDER BY stage_order
```

### 2. Cohort Retention Analysis
Groups users by their first-visit week and tracks how many return in subsequent weeks.

**Business Question answered:** "Are our customers coming back? Which cohorts are most loyal?"

### 3. A/B Test Simulation
Compares conversion rates across plan tiers (Free vs Starter vs Pro vs Enterprise).

**Business Question answered:** "Does upgrading users to a paid plan increase purchases?"

### 4. RFM Segmentation
Scores every customer on three dimensions:
- **R**ecency — how recently did they buy?
- **F**requency — how often do they buy?
- **M**onetary — how much do they spend?

Users are classified into: **Champions → Loyal → Recent → At Risk → Can't Lose → Low Value**

**Business Question answered:** "Which customers should we invest in retaining vs re-activating?"

### 5. Channel KPI Analysis
Cross-joins marketing spend data with sales data to compute per-channel efficiency.

**Business Question answered:** "Which marketing channels give us the best ROI?"

---

## 📈 Dashboard & Visualisation

The Streamlit dashboard (`dashboard/kpi_dashboard.py`) has **5 fully interactive pages**:

| Page | What You See | Why It Matters |
|---|---|---|
| **📊 KPI Overview** | 7 KPI cards (Revenue, CVR, CAC, ROAS, Buyers, LTV, Spend) + channel revenue bar chart + CAC vs ROAS efficiency scatter plot | Executive summary at a glance |
| **🔽 Funnel Analysis** | Funnel waterfall chart + step-CVR bar chart + drop-off table | Identifies where to optimise the user journey |
| **📅 Revenue & Cohorts** | Stacked monthly revenue bars + channel mix donut + orders trend line + month×channel pivot heatmap | Monitors growth and seasonality |
| **🧪 A/B Test Results** | CVR by plan tier bar chart + CVR by acquisition channel + sample size table with lift | Informs pricing & channel investment decisions |
| **🎯 RFM Segmentation** | Segment KPI cards + revenue-by-segment bar + segment size donut + avg LTV comparison | Powers personalised marketing |

**Design highlights:**
- Dark mode with a premium colour palette (electric blue #3B82F6, violet #8B5CF6, cyan #06B6D4)
- Glassmorphism-style KPI cards with hover animations
- All charts built with Plotly (interactive, hover tooltips, zero gridlines cluttering the view)
- `@st.cache_resource` and `@st.cache_data` for performant database connections

---

## ☁️ AWS Cloud Design

A production-ready AWS deployment is fully documented with two IaC options.

### Services Used

| Service | Role |
|---|---|
| **Amazon S3** | Data lake — raw (Bronze), silver, gold partitioned Parquet folders |
| **AWS Glue Crawlers** | Auto-discover schema from S3, populate Glue Data Catalog |
| **AWS Glue ETL Job** | `glue_job.py` (PySpark) — runs the same Bronze→Silver→Gold logic at scale |
| **Glue Data Catalog** | Centralised metadata store (tables, schemas, partitions) |
| **Amazon Athena** | Serverless SQL on S3 Parquet — runs funnel, cohort, RFM queries |
| **Amazon QuickSight** | Managed BI connected to Athena — enterprise dashboards |
| **Amazon EventBridge** | Cron-based scheduled pipeline runs (e.g., daily at 2am) |
| **AWS CloudFormation** | One-click stack deployment (S3 + Glue + Athena + IAM) |
| **Terraform** | Alternative IaC — multi-cloud portable |

### Estimated Cost (dev workload, ~145K rows)
| Service | Estimated Monthly |
|---|---|
| S3 (5 GB) | ~$0.15 |
| Glue (1 run/day × 5 min) | ~$3.00 |
| Athena (1 GB scanned) | ~$0.005 |
| QuickSight (1 author) | ~$18.00 |
| **Total** | **~$21/month** |

### Security Practices Applied
- ✅ S3 server-side encryption (AES-256)
- ✅ S3 bucket versioning
- ✅ IAM least-privilege (Glue role scoped to its own buckets only)
- ✅ Athena 10 GB query cost guardrail
- ✅ Glue job bookmarks (no reprocessing of old data)
- ✅ Athena results auto-deleted after 7 days
- ✅ S3 Intelligent Tiering lifecycle policy

---

## 📐 KPIs — Know These Cold

| KPI | Formula | Target Range | Table Used |
|---|---|---|---|
| **CVR** (Conversion Rate) | `Purchases / Visitors × 100` | 2–5% (e-com avg); >10% for email/direct | `fct_events` + `fct_orders` |
| **LTV** (Lifetime Value) | `Avg Order Value × 3 purchases/year` | Higher than 3× CAC | `fct_orders`, `agg_channel_kpis` |
| **CAC** (Customer Acquisition Cost) | `Total Marketing Spend / New Customers` | Should be < LTV/3 | `stg_marketing`, `dim_users` |
| **ROAS** (Return on Ad Spend) | `Revenue Attributed / Ad Spend` | ≥ 4× considered healthy | `stg_marketing` |
| **CTR** (Click-Through Rate) | `Clicks / Impressions` | 1–3% typical display | `stg_marketing` |
| **Retention** | `Return users in week N / Cohort size × 100` | Benchmark: 20%+ at week 4 | `fct_events` |

---

## 💬 Common Interview Questions & Answers

---

### Q: "Walk me through how data flows through your pipeline."

**A:**
> "Data starts as four raw CSVs — users, events (user clickstream), sales orders, and marketing campaign data. The ETL orchestrator (`pipeline.py`) first checks if the raw data exists; if not, it generates realistic synthetic data using the Faker library with proper statistical distributions. Then it runs in four stages: **ingest** loads the CSVs into a Bronze SQLite layer verbatim; **transform** cleans and types the data into a Silver staging layer (deduplication, date parsing, revenue calculations), then aggregates into a Gold layer of fact tables and dimension tables; finally **analytics** runs SQL queries on the Gold layer and exports result CSVs. The Streamlit dashboard reads directly from SQLite."

---

### Q: "Why did you use a Medallion architecture (Bronze/Silver/Gold)?"

**A:**
> "The medallion architecture directly mirrors real-world data lake design at companies like Databricks and Netflix. Bronze gives you a raw audit copy of every record — you never lose data, and you can debug any downstream issue by tracing back to raw. Silver is where you invest in data quality: deduplication, type coercion, normalisation. Gold is optimised for consumption — it's pre-aggregated so dashboards don't need to scan millions of rows at query time. This separation also means different teams can trust different layers: data engineers own Bronze and Silver, analysts own Gold."

---

### Q: "How would this scale if data volumes were 100× larger?"

**A:**
> "The AWS architecture is designed for exactly that. Locally I use SQLite and Pandas, which work well up to a few million rows. At scale, I'd switch to the AWS stack: S3 for storage (infinite scale, Parquet for columnar efficiency), AWS Glue with PySpark for distributed ETL — I've already written `glue_job.py` for this. Athena queries S3 Parquet directly with no cluster management. Parquet with partitioning (e.g., by month or channel) means Athena only scans relevant data, keeping query costs under $0.01 per analysis even at terabyte scale. The CloudFormation template deploys all of this in one command."

---

### Q: "What is RFM segmentation and why does it matter?"

**A:**
> "RFM stands for Recency, Frequency, Monetary. It's a classic customer analytics technique — you score each customer on three dimensions: how recently they purchased, how often they buy, and how much they spend. I use SQL window functions (`NTILE(4)`) to divide customers into quartiles on each dimension, then combine those scores to classify users into segments like Champions (high on all three), Loyal, At Risk, and Lost. The business value is that it powers targeted marketing: you'd offer loyalty rewards to Champions, win-back campaigns to At Risk users, and not waste budget on Low Value users. I display this on the RFM dashboard page with revenue contribution and LTV per segment."

---

### Q: "Explain funnel analysis in your project."

**A:**
> "The user journey has 5 stages: visit → product_view → add_to_cart → checkout → purchase. I generate events with realistic drop-off probabilities — roughly 65% proceed from visit to product_view, 40% add to cart, 22% reach checkout, and only about 12% complete a purchase. In the dashboard, the funnel waterfall chart shows absolute users at each stage, and a second chart shows the step-over-step conversion rate. A drop-off table shows exactly how many users were lost between each step. The business action is clear: if the biggest drop is between 'Add to Cart' and 'Checkout', that's where you investigate (e.g., shipping cost friction, form UX issues)."

---

### Q: "How did you handle the A/B test analysis?"

**A:**
> "I used plan tier (Free, Starter, Pro, Enterprise) as the test groups. The SQL joins `fct_events` (visitors per plan) with `fct_orders` (converters per plan) to compute CVR for each group. I show the CVR difference as 'lift in percentage points' — e.g., Enterprise users convert at X% vs Free users at Y%, giving a lift of Z pp. I also break CVR down by acquisition channel so you can see whether, say, email-acquired users convert better than paid search users. In a real A/B test you'd add statistical significance tests (chi-square or z-test for proportions), which I note as a potential extension."

---

### Q: "Why Streamlit instead of Tableau or Power BI?"

**A:**
> "Streamlit lets me ship a fully custom, Python-native dashboard in hours — it's code-first, which means it's version-controlled, testable, and CI/CD-friendly. For prototyping and internal analytics tools it's far faster than building in Tableau. That said, I've also included a `export_for_bi.py` script that exports all the Gold tables as Tableau `.tds` data source files and a Power BI connection guide — so stakeholders who prefer Tableau or Power BI can connect directly. For the production AWS version, Amazon QuickSight is the natural choice since it integrates natively with Athena."

---

### Q: "What tests do you have and what do they check?"

**A:**
> "The test suite has 13 pytest tests in `tests/test_pipeline.py`. They cover: (1) data generation — verifying the right number of rows and no null primary keys; (2) ingestion — confirming Bronze row counts match CSV row counts; (3) Silver transformations — checking deduplication, email normalisation, date parsing; (4) Gold layer — verifying that `fct_orders` has correct revenue calculations, `agg_channel_kpis` has no negative values, and the funnel has exactly 5 stages in the right order; (5) pipeline end-to-end — running the full pipeline and asserting all output tables exist with non-zero rows. All 13 pass."

---

### Q: "What would you improve or add if you had more time?"

**A:**
> "A few things: First, I'd add **incremental loading** — currently the pipeline rebuilds everything from scratch; in production you'd want delta/upsert logic using Glue bookmarks (already configured) or dbt's incremental models. Second, **data quality monitoring** — using Great Expectations or dbt tests to assert schema contracts, null rates, and referential integrity on every pipeline run. Third, **statistical significance** for the A/B test page using a proper chi-square test. Fourth, **real-time ingestion** — replacing CSV batch loading with streaming via Kinesis Firehose for near-real-time dashboards. Fifth, **dbt** — I'd refactor the SQL transformations into dbt models for better lineage documentation and automatic testing."

---

## 🎯 Role-Specific Angles

### If Applying for a **Data Engineer** Role
Focus on:
- The medallion architecture and why each layer exists
- The ETL orchestration logic in `pipeline.py`
- The AWS architecture (Glue + Athena + S3 + EventBridge)
- IaC with CloudFormation and Terraform
- The PySpark Glue job (`aws/glue_job.py`)
- The pytest suite and data quality testing

**Key phrase:** *"I designed this to be production-deployable from day one — the same orchestration logic runs locally on SQLite and on AWS Glue with PySpark, with a one-command CloudFormation deploy."*

---

### If Applying for a **Data Analyst** Role
Focus on:
- The KPIs and what they measure
- Funnel and cohort analysis — how to read and act on the charts
- RFM segmentation — what actionable decisions it drives
- A/B test interpretation
- The dashboard — walk through each page

**Key phrase:** *"I didn't just build charts — I made sure every analysis answers a specific business question, and the dashboard is designed so non-technical stakeholders can draw conclusions immediately."*

---

### If Applying for a **Business Intelligence / Analytics Engineer** Role
Focus on:
- The Gold layer schema design (fact tables, dimension tables, aggregates)
- The KPI definitions documentation (`docs/kpi_definitions.md`)
- The data dictionary (`docs/data_dictionary.md`)
- BI tool exports (Tableau .tds, Power BI guide)
- Why the multi-layer architecture makes BI tools faster

**Key phrase:** *"The Gold layer is designed as a star schema — fact tables joined to dimension tables — so any BI tool including Tableau, Power BI, or QuickSight can connect and build reports without needing to know the raw data structure."*

---

### If Applying for a **Cloud / Solutions Architect** Role
Focus on:
- The AWS service mapping (local → production)
- Cost estimation (~$21/month for dev, scalable by design)
- Security: IAM least-privilege, encryption, query cost guardrails
- IaC: CloudFormation template + Terraform alternative
- Scalability: S3 + Parquet + Athena serverless design
- EventBridge for scheduling

**Key phrase:** *"The architecture uses fully managed, serverless services — S3, Glue, Athena — so there are no servers to manage, and the cost scales linearly with data volume rather than requiring over-provisioned clusters."*

---

## 📏 Metrics to Quote

Use these numbers confidently when asked:

| Metric | Value |
|---|---|
| Users in dataset | 5,000 |
| User behaviour events | 60,000 |
| Sales orders | 8,000 |
| Marketing campaigns | 20 |
| Products | 50 |
| Marketing channels | 6 |
| Database tables (total) | 13 (4 raw + 4 silver + 5 gold) |
| Dashboard pages | 5 |
| Analytics queries | 6 |
| Unit tests | 13 |
| Estimated AWS cost | ~$21/month |
| Lines of Python code | ~2,000+ |
| Pipeline runtime (local) | ~40 seconds |
| BI export formats | 3 (CSV, Excel, Tableau .tds) |

---

## 🗣 Power Phrases for Interviews

> *"The pipeline mirrors real-world production patterns — Bronze/Silver/Gold is the same medallion architecture used by Databricks, Airbnb, and Netflix."*

> *"I built it so the same business logic runs locally in Python/SQLite and at scale in AWS Glue/PySpark — the deployment environment is swappable without changing analytical queries."*

> *"Every KPI in the dashboard has a documented formula, source table, and business benchmark — I wrote a full KPI glossary so stakeholders and future engineers know exactly what each metric means."*

> *"The dashboard isn't just pretty charts — each page answers a specific business question that a product manager or CMO would actually ask."*

> *"Infrastructure as Code was a deliberate choice — the entire AWS stack deploys in one CloudFormation command, and I provide a Terraform alternative for multi-cloud portability."*

---

*Document generated: February 2026 | Project: Cloud Infrastructure Metrics & Log Analytics Pipeline*
