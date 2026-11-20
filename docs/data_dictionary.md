# Data Dictionary

> **Project:** Cloud Infrastructure Metrics & Log Analytics Pipeline

---

## `raw_users` / `stg_users` / `dim_users`

| Column | Type | Description |
|---|---|---|
| `user_id` | TEXT (PK) | Unique user identifier (e.g., `U00001`) |
| `name` | TEXT | Full name |
| `email` | TEXT | Email address (lowercased in silver) |
| `country` | TEXT | ISO-2 country code |
| `channel` | TEXT | Acquisition channel (see KPI definitions) |
| `acquisition_date` | DATE | Date the user was first acquired |
| `age_group` | TEXT | Bucketed age range (e.g., `25-34`) |
| `plan` | TEXT | Product plan: `free`, `starter`, `pro`, `enterprise` |
| `plan_rank` | INT | Numeric rank of plan (0=free → 3=enterprise) *(silver only)* |

---

## `raw_user_events` / `stg_events` / `fct_events`

| Column | Type | Description |
|---|---|---|
| `event_id` | TEXT (PK) | UUID for the event |
| `user_id` | TEXT (FK) | References `dim_users.user_id` |
| `session_id` | TEXT | Browser/app session identifier |
| `stage` | TEXT | Funnel stage: `visit`, `product_view`, `add_to_cart`, `checkout`, `purchase` |
| `stage_order` | INT | Numeric order of the stage (1–5) *(silver only)* |
| `product_id` | TEXT | Product viewed/purchased (NULL for visit stage) |
| `timestamp` | DATETIME | Event timestamp |
| `date` | DATE | Date part of timestamp *(silver only)* |
| `week` | TEXT | ISO week period (e.g., `2025-W11`) *(silver only)* |
| `month` | TEXT | Month period (e.g., `2025-03`) *(silver only)* |
| `device` | TEXT | Device type: `desktop`, `mobile`, `tablet` |
| `country` | TEXT | ISO-2 country code |
| `channel` | TEXT | Joined from `dim_users` *(gold only)* |
| `plan` | TEXT | Joined from `dim_users` *(gold only)* |
| `age_group` | TEXT | Joined from `dim_users` *(gold only)* |
| `acquisition_date` | DATE | Joined from `dim_users` *(gold only)* |

---

## `raw_sales` / `stg_sales` / `fct_orders`

| Column | Type | Description |
|---|---|---|
| `order_id` | TEXT | Order identifier |
| `line_id` | INT | Line item number within the order |
| `user_id` | TEXT (FK) | References `dim_users.user_id` |
| `product_id` | TEXT (FK) | References `dim_products.product_id` |
| `quantity` | INT | Number of units purchased |
| `unit_price` | REAL | Price per unit (pre-discount) |
| `discount_pct` | REAL | Discount applied (0–100) |
| `net_revenue` | REAL | `unit_price × quantity × (1 - discount_pct/100)` *(silver+)* |
| `order_date` | DATE | Date of order |
| `month` | TEXT | Month period *(silver+)* |
| `quarter` | TEXT | Quarter period (e.g., `2025-Q1`) *(silver+)* |
| `status` | TEXT | `completed`, `returned`, `cancelled` |
| `channel` | TEXT | Channel at time of purchase |
| `country` | TEXT | Country of purchaser |
| `plan` | TEXT | Joined from `dim_users` *(gold only)* |
| `age_group` | TEXT | Joined from `dim_users` *(gold only)* |
| `acquisition_date` | DATE | Joined from `dim_users` *(gold only)* |

---

## `raw_marketing` / `stg_marketing` / `dim_campaigns`

| Column | Type | Description |
|---|---|---|
| `campaign_id` | TEXT (PK) | Campaign identifier (e.g., `CMP-001`) |
| `campaign_name` | TEXT | Human-readable campaign name |
| `channel` | TEXT | Acquisition channel |
| `start_date` | DATE | Campaign start |
| `end_date` | DATE | Campaign end |
| `budget` | REAL | Allocated budget ($) |
| `spend` | REAL | Actual spend ($) |
| `impressions` | INT | Total ad impressions |
| `clicks` | INT | Total clicks |
| `conversions` | INT | Attributed conversions |
| `revenue_attributed` | REAL | Revenue attributed to campaign ($) |
| `ctr` | REAL | Click-through rate = clicks / impressions *(silver+)* |
| `cvr` | REAL | Conversion rate = conversions / clicks *(silver+)* |
| `cac` | REAL | Cost per acquisition = spend / conversions *(silver+)* |
| `roas` | REAL | Return on ad spend = revenue / spend *(silver+)* |

---

## `dim_products`

| Column | Type | Description |
|---|---|---|
| `product_id` | TEXT (PK) | Product identifier (e.g., `PROD-001`) |
| `category` | TEXT | Product category: `Electronics`, `Apparel`, `Home`, `Books`, `Sports` |

---

## `agg_channel_kpis`

| Column | Type | Description |
|---|---|---|
| `channel` | TEXT (PK) | Acquisition channel |
| `buyers` | INT | Distinct buyers via this channel |
| `total_revenue` | REAL | Total net revenue from completed orders |
| `avg_order_value` | REAL | Mean net revenue per order line |
| `ltv_estimate` | REAL | `avg_order_value × 3` (simplified LTV) |
| `total_spend` | REAL | Total marketing spend on channel |
| `total_conversions` | INT | Total campaign conversions |
| `avg_cvr` | REAL | Average campaign CVR |
| `avg_cac` | REAL | Average cost per acquisition |
| `avg_roas` | REAL | Average return on ad spend |
