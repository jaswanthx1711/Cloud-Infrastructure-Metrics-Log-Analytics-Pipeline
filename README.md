# ☁️ Cloud Infrastructure Metrics & Log Analytics Pipeline (AWS)

> Built a repeatable ETL pipeline (SQL + Python) to consolidate sales, user events, and marketing data into a multi-layer analytics schema. Conducts funnel and cohort analyses, tracks CVR/LTV/CAC/ROAS, and delivers insights via interactive dashboards. Deployable locally (SQLite + Streamlit) or on AWS (S3 + Glue + Athena + QuickSight).

---

## 📐 Architecture

### Local (Development)
```
data/raw/*.csv  →  Bronze (SQLite)  →  Silver (stg_*)  →  Gold (fct_*, dim_*, agg_*)  →  Streamlit Dashboard
```

### AWS (Production)
```
S3 (raw/)  →  Glue Crawler  →  Glue ETL Job  →  S3 (silver/ + gold/ Parquet)  →  Athena  →  QuickSight
```

See [`aws/architecture.md`](aws/architecture.md) for the full diagram and deployment guide.

---

## 🗂️ Project Structure

```
E-Commerce-Business-Analytics-KPI-Pipeline/
│
├── etl/
│   ├── generate_data.py      ← Synthetic data generator (Faker + NumPy)
│   ├── ingest.py             ← Bronze layer: CSV → SQLite
│   ├── transform.py          ← Silver → Gold transformations
│   ├── pipeline.py           ← Master ETL orchestrator ▶ run this
│   └── export_for_bi.py      ← Tableau / Power BI export
│
├── aws/
│   ├── glue_job.py           ← AWS Glue PySpark ETL job
│   ├── cloudformation.yaml   ← One-click AWS stack (S3 + Glue + Athena)
│   ├── architecture.md       ← AWS architecture docs + deploy guide
│   └── terraform/
│       └── main.tf           ← Terraform alternative to CloudFormation
│
├── sql/
│   ├── bronze/               ← Raw table DDL
│   ├── silver/               ← Staging table DDL
│   ├── gold/                 ← Dimension / Fact / Aggregate DDL
│   └── analytics/
│       ├── 04_funnel_analysis.sql
│       ├── 05_cohort_analysis.sql
│       └── 06_ab_test_segmentation.sql
│
├── dashboard/
│   └── kpi_dashboard.py      ← Streamlit dashboard (5 pages)
│
├── data/
│   ├── raw/                  ← Source CSVs (generated or real)
│   ├── processed/            ← Analytics export CSVs
│   ├── bi_exports/           ← Tableau .tds + Power BI guide + Excel
│   └── analytics.db          ← SQLite analytics database
│
├── docs/
│   ├── kpi_definitions.md    ← KPI glossary (CVR, LTV, CAC, ROAS…)
│   ├── data_dictionary.md    ← Field-level schema docs
│   └── handover_notebook.md  ← Reproduction & maintenance guide
│
├── tests/
│   └── test_pipeline.py      ← 13 Pytest unit tests
│
└── requirements.txt
```

---

## 🚀 Quickstart (Local)

```bash
# 1. Clone and install
git clone <repo-url>
cd E-Commerce-Business-Analytics-KPI-Pipeline
pip install -r requirements.txt

# 2. Run the full ETL pipeline (~40s)
python3 etl/pipeline.py

# 3. Launch the dashboard
python3 -m streamlit run dashboard/kpi_dashboard.py

# 4. Export for Tableau / Power BI
python3 etl/export_for_bi.py
```

Dashboard → **http://localhost:8501**

---

## ☁️ Quickstart (AWS)

```bash
# Deploy infrastructure (CloudFormation)
aws cloudformation deploy \
  --template-file aws/cloudformation.yaml \
  --stack-name cloud-metrics-dev \
  --parameter-overrides ProjectName=cloud-metrics Environment=dev \
      GlueJobScriptPath=s3://my-scripts-bucket/scripts/glue_job.py \
  --capabilities CAPABILITY_IAM

# Upload data & run pipeline
aws s3 cp data/raw/ s3://<datalake-bucket>/raw/ --recursive
aws glue start-crawler --name cloud-metrics-dev-bronze-crawler
aws glue start-job-run --job-name cloud-metrics-dev-etl-job
```

See [`aws/architecture.md`](aws/architecture.md) for full instructions.

---

## 📊 Key Analyses

| Analysis | SQL File | Dashboard Page |
|---|---|---|
| Funnel conversion & drop-off | `sql/analytics/04_funnel_analysis.sql` | 🔽 Funnel Analysis |
| Cohort retention & LTV | `sql/analytics/05_cohort_analysis.sql` | 📅 Revenue & Cohorts |
| A/B test — plan tier CVR | `sql/analytics/06_ab_test_segmentation.sql` | 🧪 A/B Test Results |
| RFM segmentation | `sql/analytics/06_ab_test_segmentation.sql` | 🎯 RFM Segmentation |
| Channel KPIs (CAC, ROAS) | Gold layer agg | 📊 KPI Overview |

---

## 📈 KPIs Tracked

| KPI | Definition |
|---|---|
| **CVR** | Completed purchases / Total visitors |
| **LTV** | Avg order value × 3 (proxy for lifetime value) |
| **CAC** | Total ad spend / New buyers |
| **ROAS** | Total revenue / Total ad spend |
| **CTR** | Clicks / Impressions |
| **Retention** | Repeat buyers in cohort Nth month |

---

## 🧪 Tests

```bash
python3 -m pytest tests/ -v
# 13/13 tests pass ✅
```

---

## 📤 BI Tool Exports

After running `python3 etl/export_for_bi.py`, the `data/bi_exports/` folder contains:

| File | Purpose |
|---|---|
| `agg_channel_kpis.csv` | Channel KPI summary |
| `fct_orders.csv` | Order-level fact table |
| `fct_events.csv` | User funnel events |
| `monthly_revenue.csv` | Revenue by month × channel |
| `rfm_segments.csv` | RFM-scored users |
| `analytics_export.xlsx` | All tables in one Excel workbook |
| `cloud_metrics.tds` | Tableau Data Source (open in Tableau Desktop) |
| `POWERBI_CONNECTION_GUIDE.md` | Power BI connection + DAX measures |

---

## 📚 Documentation

| Doc | Contents |
|---|---|
| [`docs/kpi_definitions.md`](docs/kpi_definitions.md) | KPI glossary and business definitions |
| [`docs/data_dictionary.md`](docs/data_dictionary.md) | Schema for all Bronze / Silver / Gold tables |
| [`docs/handover_notebook.md`](docs/handover_notebook.md) | Setup, run, refresh, troubleshoot |
| [`aws/architecture.md`](aws/architecture.md) | AWS architecture, cost estimate, deploy guide |

---

## 🛠️ Tech Stack

| Layer | Local | AWS |
|---|---|---|
| Storage | SQLite | S3 (Parquet) |
| ETL | Python (Pandas) | AWS Glue (PySpark) |
| SQL | SQLite | Amazon Athena |
| Dashboard | Streamlit + Plotly | Amazon QuickSight |
| IaC | — | CloudFormation / Terraform |
| Scheduling | Manual | Amazon EventBridge |
