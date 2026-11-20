# Handover & Reproduction Guide

> **Project:** Cloud Infrastructure Metrics & Log Analytics Pipeline  
> **EPITA | Oct 2025 – Dec 2025**

---

## 🎯 Purpose

This document explains how any new analyst or engineer can:
1. Set up the project from scratch
2. Run the full ETL pipeline
3. Reproduce all analyses
4. Launch the interactive dashboard
5. Update and maintain the dashboards going forward

---

## ⚙️ Prerequisites

| Requirement | Version |
|---|---|
| Python | ≥ 3.10 |
| pip | ≥ 23.x |
| Git | any |
| (Optional) Tableau / Power BI | Desktop |

---

## 🚀 Quickstart (5 minutes)

```bash
# 1. Clone the repo
git clone <repo-url>
cd E-Commerce-Business-Analytics-KPI-Pipeline

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the full pipeline (generates data + builds DB + exports CSVs)
python etl/pipeline.py

# 5. Launch the dashboard
streamlit run dashboard/kpi_dashboard.py
```

The pipeline will:
1. Generate 5,000 synthetic users, 60K+ events, 8K+ order lines, 20 campaigns
2. Load them into `data/analytics.db` (SQLite)
3. Apply bronze → silver → gold transformations
4. Export 6 analysis CSVs to `data/processed/`

---

## 📂 What Each File Does

### ETL Layer

| File | Purpose |
|---|---|
| `etl/generate_data.py` | One-time synthetic data generator (Faker + NumPy) |
| `etl/ingest.py` | Reads raw CSVs → bronze SQLite tables |
| `etl/transform.py` | Runs all silver + gold transformations (Python + Pandas) |
| `etl/pipeline.py` | Master orchestrator — run this to refresh everything |

### SQL Layer

| File | Purpose |
|---|---|
| `sql/bronze/01_create_raw_tables.sql` | Raw table DDL reference |
| `sql/silver/02_create_staging_tables.sql` | Cleaned staging model DDL |
| `sql/gold/03_create_dim_fact_tables.sql` | Dimension + fact table DDL |
| `sql/analytics/04_funnel_analysis.sql` | Funnel conversion queries |
| `sql/analytics/05_cohort_analysis.sql` | Cohort retention + LTV queries |
| `sql/analytics/06_ab_test_segmentation.sql` | A/B test + RFM segmentation queries |

### Dashboard

| File | Purpose |
|---|---|
| `dashboard/kpi_dashboard.py` | 5-page Streamlit dashboard |

---

## 🔄 How to Refresh the Data

If you have a new dataset (real data):

1. Drop your CSVs into `data/raw/` with the **exact same column names** as the schemas in `docs/data_dictionary.md`
2. Re-run the pipeline:
   ```bash
   python etl/pipeline.py
   ```
3. The dashboard auto-refreshes from the updated database.

---

## 📊 Exported Analysis Files

After running the pipeline, `data/processed/` will contain:

| File | Description |
|---|---|
| `funnel_conversion.csv` | Funnel stage conversion rates |
| `cohort_retention.csv` | Weekly cohort retention matrix |
| `monthly_revenue.csv` | Revenue by month + channel |
| `channel_kpis.csv` | CVR / LTV / CAC / ROAS per channel |
| `product_performance.csv` | Top 20 products by revenue |
| `ab_test_plan_cvr.csv` | Conversion rate by plan tier |
| `rfm_segmentation.csv` | RFM scores per user |

These CSVs can be imported directly into **Power BI** or **Tableau**.

---

## 🔗 Connecting to Power BI / Tableau

### Power BI

1. Open Power BI Desktop
2. `Home → Get Data → Text/CSV`
3. Select any CSV from `data/processed/`
4. Or connect directly to the SQLite DB via ODBC:
   - Install SQLite ODBC driver
   - `Home → Get Data → ODBC → analytics.db`

### Tableau

1. Open Tableau Desktop
2. `Connect → To a File → Text File`
3. Select any CSV from `data/processed/`
4. Or use the Other Databases (ODBC) connector with SQLite

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

Tests cover:
- Data generation correctness
- Silver layer transformations (dedup, typing, formula accuracy)
- KPI formula validation (CVR bounds, ROAS non-negativity)
- Database table existence checks

---

## 📈 Adding a New Analysis

1. Write your SQL in `sql/analytics/07_your_analysis.sql`
2. Add it to the `analyses` dict in `etl/pipeline.py` → `_run_analytics()`
3. Add a new Streamlit page in `dashboard/kpi_dashboard.py`
4. Document the KPI in `docs/kpi_definitions.md`
5. Add a unit test in `tests/test_pipeline.py`

---

## 🆘 Troubleshooting

| Problem | Solution |
|---|---|
| `FileNotFoundError: users.csv not found` | Run `python etl/generate_data.py` first |
| `ModuleNotFoundError: No module named 'streamlit'` | Run `pip install -r requirements.txt` |
| Dashboard shows "Database not found" | Run `python etl/pipeline.py` first |
| SQLite `FULL OUTER JOIN` error | SQLite ≥ 3.39 required; or use Python transform instead |

---

## 👤 Contacts

| Role | Name |
|---|---|
| Project Lead | Jaswanth Thathireddy |
| Institution | EPITA |
| Period | Oct 2025 – Dec 2025 |
