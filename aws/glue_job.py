"""
glue_job.py — AWS Glue ETL Job
Cloud Infrastructure Metrics & Log Analytics Pipeline

This script is designed to run as an AWS Glue Python Shell job.
It replaces the local `etl/pipeline.py` and operates on S3 + AWS Glue Catalog.

Architecture:
    S3 (raw CSVs) → Glue Crawler → Glue Catalog (Bronze)
                 → Glue Job (this file) → S3 (silver/gold Parquet)
                 → Athena (query) → QuickSight (dashboard)

Environment Variables (set in Glue Job Parameters):
    S3_BUCKET      : e.g. my-cloud-metrics-bucket
    DATABASE_NAME  : Glue catalog DB name, e.g. cloud_metrics
    AWS_REGION     : e.g. eu-west-1
"""

import sys
import boto3
import json
from datetime import datetime

# AWS Glue-specific imports (available in Glue runtime)
try:
    from awsglue.transforms import *
    from awsglue.utils import getResolvedOptions
    from pyspark.context import SparkContext
    from awsglue.context import GlueContext
    from awsglue.job import Job
    GLUE_RUNTIME = True
except ImportError:
    # Allow local import/syntax checking without Glue installed
    GLUE_RUNTIME = False

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Job parameters ───────────────────────────────────────────────────────
def get_args():
    if GLUE_RUNTIME:
        args = getResolvedOptions(sys.argv, [
            "JOB_NAME", "S3_BUCKET", "DATABASE_NAME", "AWS_REGION"
        ])
    else:
        # Local defaults for testing
        args = {
            "JOB_NAME":      "cloud-metrics-etl",
            "S3_BUCKET":     "my-cloud-metrics-bucket",
            "DATABASE_NAME": "cloud_metrics",
            "AWS_REGION":    "eu-west-1",
        }
    return args


# ── S3 paths ─────────────────────────────────────────────────────────────
def get_paths(bucket: str) -> dict:
    return {
        "raw":    f"s3://{bucket}/raw/",
        "silver": f"s3://{bucket}/silver/",
        "gold":   f"s3://{bucket}/gold/",
    }


# ── Bronze → Silver transformations (SQL via Spark) ─────────────────────
SILVER_TRANSFORMS = {
    "stg_users": """
        SELECT
            user_id,
            email,
            CAST(signup_date AS DATE)  AS signup_date,
            LOWER(TRIM(plan))          AS plan,
            LOWER(TRIM(channel))       AS channel,
            UPPER(TRIM(country))       AS country
        FROM bronze_users
        WHERE user_id IS NOT NULL AND email IS NOT NULL
    """,
    "stg_orders": """
        SELECT
            order_id,
            user_id,
            CAST(order_date AS DATE)   AS order_date,
            SUBSTR(order_date, 1, 7)   AS month,
            product_id,
            product_name,
            category,
            CAST(quantity AS INT)      AS quantity,
            CAST(unit_price AS DOUBLE) AS unit_price,
            COALESCE(CAST(discount AS DOUBLE), 0.0) AS discount,
            CAST(quantity AS DOUBLE)
                * CAST(unit_price AS DOUBLE)
                * (1 - COALESCE(CAST(discount AS DOUBLE), 0.0)) AS net_revenue,
            LOWER(TRIM(status))        AS status,
            LOWER(TRIM(channel))       AS channel,
            LOWER(TRIM(plan))          AS plan
        FROM bronze_sales
        WHERE order_id IS NOT NULL AND user_id IS NOT NULL
    """,
    "stg_events": """
        SELECT
            event_id,
            user_id,
            session_id,
            CAST(event_date AS DATE)   AS event_date,
            LOWER(TRIM(stage))         AS stage,
            CAST(stage_order AS INT)   AS stage_order,
            LOWER(TRIM(device))        AS device,
            LOWER(TRIM(plan))          AS plan
        FROM bronze_user_events
        WHERE event_id IS NOT NULL
    """,
    "stg_marketing": """
        SELECT
            CAST(week AS DATE)            AS week,
            LOWER(TRIM(channel))          AS channel,
            CAST(spend AS DOUBLE)         AS spend,
            CAST(impressions AS BIGINT)   AS impressions,
            CAST(clicks AS BIGINT)        AS clicks,
            CAST(conversions AS BIGINT)   AS conversions,
            CASE WHEN impressions > 0
                 THEN CAST(clicks AS DOUBLE)/impressions ELSE 0 END AS ctr,
            CASE WHEN clicks > 0
                 THEN CAST(conversions AS DOUBLE)/clicks ELSE 0 END AS cvr,
            CASE WHEN conversions > 0
                 THEN CAST(spend AS DOUBLE)/conversions ELSE NULL END AS cac
        FROM bronze_marketing
        WHERE week IS NOT NULL
    """,
}

# ── Gold layer aggregations ─────────────────────────────────────────────
GOLD_TRANSFORMS = {
    "agg_channel_kpis": """
        SELECT
            o.channel,
            COUNT(DISTINCT o.user_id)             AS buyers,
            ROUND(SUM(o.net_revenue), 2)          AS total_revenue,
            ROUND(AVG(o.net_revenue), 2)          AS avg_order_value,
            ROUND(AVG(o.net_revenue) * 3, 2)      AS ltv_estimate,
            COALESCE(SUM(m.spend), 0)             AS total_spend,
            COUNT(DISTINCT o.order_id)            AS conversions,
            ROUND(AVG(o.net_revenue)/
                  NULLIF(COUNT(DISTINCT o.user_id),0),2) AS avg_cvr,
            ROUND(COALESCE(SUM(m.spend),0)/
                  NULLIF(COUNT(DISTINCT o.user_id),0),2) AS avg_cac,
            ROUND(SUM(o.net_revenue)/
                  NULLIF(COALESCE(SUM(m.spend),0),0),2)  AS avg_roas
        FROM stg_orders o
        LEFT JOIN (
            SELECT channel, SUM(spend) AS spend
            FROM stg_marketing GROUP BY channel
        ) m ON o.channel = m.channel
        WHERE o.status = 'completed'
        GROUP BY o.channel
    """,
}


def run_glue_job():
    args = get_args()
    bucket   = args["S3_BUCKET"]
    db_name  = args["DATABASE_NAME"]
    paths    = get_paths(bucket)

    if not GLUE_RUNTIME:
        logger.info("⚠  Not running in Glue runtime — printing plan only.\n")
        logger.info(f"  S3 Bucket   : s3://{bucket}/")
        logger.info(f"  Raw Zone    : {paths['raw']}")
        logger.info(f"  Silver Zone : {paths['silver']}")
        logger.info(f"  Gold Zone   : {paths['gold']}")
        logger.info(f"  Glue DB     : {db_name}")
        logger.info("\n  Silver tables : " + ", ".join(SILVER_TRANSFORMS))
        logger.info("  Gold tables   : " + ", ".join(GOLD_TRANSFORMS))
        return

    # ── Glue context ──────────────────────────────────────────────────
    sc          = SparkContext()
    glue_context = GlueContext(sc)
    spark        = glue_context.spark_session
    job          = Job(glue_context)
    job.init(args["JOB_NAME"], args)

    # ── Step 1: Load raw tables from S3 / Glue Catalog ───────────────
    logger.info("[1/3] Loading bronze (raw) tables from Glue Catalog …")
    raw_tables = ["bronze_users", "bronze_sales", "bronze_user_events", "bronze_marketing"]
    for tbl in raw_tables:
        df = glue_context.create_dynamic_frame.from_catalog(
            database=db_name, table_name=tbl
        ).toDF()
        df.createOrReplaceTempView(tbl.replace("bronze_", "bronze_"))
        logger.info(f"  Loaded {tbl}: {df.count():,} rows")

    # ── Step 2: Silver transformations ───────────────────────────────
    logger.info("[2/3] Running Silver transformations …")
    for tbl_name, sql in SILVER_TRANSFORMS.items():
        df = spark.sql(sql)
        df.createOrReplaceTempView(tbl_name)
        out_path = paths["silver"] + tbl_name + "/"
        df.write.mode("overwrite").parquet(out_path)
        logger.info(f"  {tbl_name} → {out_path}  ({df.count():,} rows)")

    # ── Step 3: Gold aggregations ─────────────────────────────────────
    logger.info("[3/3] Building Gold aggregations …")
    for tbl_name, sql in GOLD_TRANSFORMS.items():
        df = spark.sql(sql)
        out_path = paths["gold"] + tbl_name + "/"
        df.write.mode("overwrite").parquet(out_path)
        logger.info(f"  {tbl_name} → {out_path}  ({df.count():,} rows)")

    job.commit()
    logger.info("✅  Glue job complete.")


if __name__ == "__main__":
    run_glue_job()
