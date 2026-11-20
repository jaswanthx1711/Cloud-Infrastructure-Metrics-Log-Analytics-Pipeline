"""
config.py
Centralised configuration for the E-Commerce Analytics Pipeline.
Values can be overridden via a .env file (loaded by python-dotenv).
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; env vars must be set manually

REPO_ROOT = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(REPO_ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
BI_EXPORTS_DIR = os.path.join(DATA_DIR, "bi_exports")
DB_PATH = os.path.join(DATA_DIR, "analytics.db")

# RFM analysis cutoff date — override via PIPELINE_CUTOFF_DATE env var
PIPELINE_CUTOFF_DATE = os.getenv("PIPELINE_CUTOFF_DATE", "2026-01-01")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
