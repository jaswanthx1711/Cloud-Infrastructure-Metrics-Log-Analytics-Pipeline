"""
generate_data.py
Generates realistic synthetic datasets for the E-Commerce Analytics Pipeline.
Outputs CSV files to data/raw/:
  - sales.csv          : transactional sales records
  - user_events.csv    : clickstream / user behaviour funnel events
  - marketing.csv      : campaign-level spend and attribution data
  - users.csv          : user dimension (demographics, acquisition channel)
"""

import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
random.seed(42)
np.random.seed(42)

# ── Config ─────────────────────────────────────────────────────────────
RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

START_DATE  = datetime(2025, 1, 1)
END_DATE    = datetime(2025, 12, 31)
N_USERS     = 5_000
N_EVENTS    = 60_000
N_ORDERS    = 8_000
N_CAMPAIGNS = 20

CHANNELS  = ["organic_search", "paid_search", "social_media", "email", "referral", "direct"]
STAGES    = ["visit", "product_view", "add_to_cart", "checkout", "purchase"]
PRODUCTS  = [f"PROD-{i:03d}" for i in range(1, 51)]
COUNTRIES = ["US", "UK", "DE", "FR", "CA", "AU", "IN", "BR"]


def rand_date(start: datetime = START_DATE, end: datetime = END_DATE) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


# ── 1. Users ───────────────────────────────────────────────────────────
def generate_users() -> pd.DataFrame:
    print("  → Generating users …")
    rows = []
    for i in range(1, N_USERS + 1):
        acq_date = rand_date(START_DATE, END_DATE - timedelta(days=30))
        rows.append({
            "user_id":          f"U{i:05d}",
            "name":             fake.name(),
            "email":            fake.email(),
            "country":          random.choice(COUNTRIES),
            "channel":          random.choice(CHANNELS),
            "acquisition_date": acq_date.date(),
            "age_group":        random.choice(["18-24", "25-34", "35-44", "45-54", "55+"]),
            "plan":             random.choice(["free", "starter", "pro", "enterprise"]),
        })
    return pd.DataFrame(rows)


# ── 2. User Events (funnel) ────────────────────────────────────────────
def generate_events(users: pd.DataFrame) -> pd.DataFrame:
    print("  → Generating user events …")
    rows = []
    user_ids = users["user_id"].tolist()
    # Build a lookup dict for performance (avoid repeated .loc[] in inner loop)
    user_country = users.set_index("user_id")["country"].to_dict()

    for _ in range(N_EVENTS):
        uid  = random.choice(user_ids)
        # simulate funnel drop-off probabilities
        stage_probs = [1.0, 0.65, 0.40, 0.22, 0.12]
        max_stage   = np.random.choice(range(5), p=np.array(stage_probs) / sum(stage_probs))
        ts = rand_date()
        # session_id generated ONCE per session (shared across all stage events in this session)
        session_id = fake.uuid4()[:8]
        for s_idx in range(max_stage + 1):
            rows.append({
                "event_id":   fake.uuid4(),
                "user_id":    uid,
                "session_id": session_id,
                "stage":      STAGES[s_idx],
                "product_id": random.choice(PRODUCTS) if s_idx >= 1 else None,
                "timestamp":  ts + timedelta(minutes=s_idx * random.randint(1, 10)),
                "device":     random.choice(["desktop", "mobile", "tablet"]),
                "country":    user_country[uid],
            })
    return pd.DataFrame(rows)


# ── 3. Sales ───────────────────────────────────────────────────────────
def generate_sales(users: pd.DataFrame) -> pd.DataFrame:
    print("  → Generating sales …")
    rows = []
    user_channel = users.set_index("user_id")["channel"].to_dict()
    user_country = users.set_index("user_id")["country"].to_dict()
    # Choose only users who reached 'purchase' stage (approx 12%)
    buyers = random.sample(users["user_id"].tolist(), min(N_ORDERS, N_USERS))
    for i, uid in enumerate(buyers, start=1):
        n_items    = random.randint(1, 5)
        order_date = rand_date()
        for j in range(n_items):
            quantity   = random.randint(1, 4)
            unit_price = round(random.uniform(9.99, 299.99), 2)
            rows.append({
                "order_id":     f"ORD-{i:05d}",
                "line_id":      j + 1,
                "user_id":      uid,
                "product_id":   random.choice(PRODUCTS),
                "quantity":     quantity,
                "unit_price":   unit_price,
                "discount_pct": random.choice([0, 0, 0, 5, 10, 15, 20]),
                "order_date":   order_date.date(),
                "status":       random.choices(
                    ["completed", "returned", "cancelled"],
                    weights=[0.85, 0.10, 0.05]
                )[0],
                "channel": user_channel[uid],
                "country": user_country[uid],
            })
    df = pd.DataFrame(rows)
    df["revenue"] = (df["unit_price"] * df["quantity"] * (1 - df["discount_pct"] / 100)).round(2)
    return df


# ── 4. Marketing Campaigns ─────────────────────────────────────────────
def generate_marketing() -> pd.DataFrame:
    print("  → Generating marketing data …")
    rows = []
    for i in range(1, N_CAMPAIGNS + 1):
        channel = random.choice(CHANNELS)
        start   = rand_date(START_DATE, END_DATE - timedelta(days=30))
        end     = start + timedelta(days=random.randint(7, 60))
        spend   = round(random.uniform(500, 25_000), 2)
        impr    = random.randint(10_000, 500_000)
        clicks  = int(impr * random.uniform(0.01, 0.08))
        conv    = int(clicks * random.uniform(0.02, 0.15))
        rows.append({
            "campaign_id":        f"CMP-{i:03d}",
            "campaign_name":      f"{channel.replace('_',' ').title()} Campaign {i}",
            "channel":            channel,
            "start_date":         start.date(),
            "end_date":           end.date(),
            "budget":             spend,
            "spend":              round(spend * random.uniform(0.6, 1.0), 2),
            "impressions":        impr,
            "clicks":             clicks,
            "conversions":        conv,
            "revenue_attributed": round(conv * random.uniform(30, 200), 2),
        })
    return pd.DataFrame(rows)


# ── Main ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🔧 Generating synthetic datasets …")

    users     = generate_users()
    events    = generate_events(users)
    sales     = generate_sales(users)
    marketing = generate_marketing()

    users.to_csv(    os.path.join(RAW_DIR, "users.csv"),        index=False)
    events.to_csv(   os.path.join(RAW_DIR, "user_events.csv"),  index=False)
    sales.to_csv(    os.path.join(RAW_DIR, "sales.csv"),        index=False)
    marketing.to_csv(os.path.join(RAW_DIR, "marketing.csv"),    index=False)

    print(f"\n✅ Saved to {RAW_DIR}/")
    print(f"   users.csv       → {len(users):,} rows")
    print(f"   user_events.csv → {len(events):,} rows")
    print(f"   sales.csv       → {len(sales):,} rows")
    print(f"   marketing.csv   → {len(marketing):,} rows")
