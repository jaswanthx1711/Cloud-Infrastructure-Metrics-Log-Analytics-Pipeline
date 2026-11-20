# KPI Definitions

> **Project:** Cloud Infrastructure Metrics & Log Analytics Pipeline  
> **Team:** EPITA Analytics — Oct 2025 – Dec 2025  
> **Purpose:** Single source of truth for all business KPIs tracked in this project.

---

## 📐 Core KPIs

### CVR – Conversion Rate
| Field | Value |
|---|---|
| **Definition** | The percentage of visitors who complete a desired action (e.g., purchase). |
| **Formula** | `CVR = (Conversions / Total Visitors) × 100` |
| **Granularities** | Overall · Per Channel · Per Plan · Per Device |
| **Source Table** | `fct_events` + `fct_orders` |
| **Good range** | 2–5% (e-commerce average); >10% for email / direct |

---

### LTV – Customer Lifetime Value
| Field | Value |
|---|---|
| **Definition** | Estimated total revenue a customer will generate over their relationship with the business. |
| **Formula (simplified)** | `LTV = Avg Order Value × Purchase Frequency × Customer Lifespan` |
| **Formula (used here)** | `LTV_estimate = avg_order_value × 3` (assumes ~3 purchases/year) |
| **Source Table** | `fct_orders`, `agg_channel_kpis` |
| **Why it matters** | Determines how much to spend on acquisition (CAC should be < LTV). |

---

### CAC – Customer Acquisition Cost
| Field | Value |
|---|---|
| **Definition** | Total marketing spend divided by the number of new customers acquired. |
| **Formula** | `CAC = Total Marketing Spend / New Customers Acquired` |
| **Source Table** | `stg_marketing`, `dim_users` |
| **Health check** | CAC should be < LTV/3 for a sustainable business. |

---

### ROAS – Return on Ad Spend
| Field | Value |
|---|---|
| **Definition** | Revenue earned for every dollar spent on advertising. |
| **Formula** | `ROAS = Revenue Attributed / Ad Spend` |
| **Source Table** | `stg_marketing` |
| **Benchmark** | ROAS ≥ 4× is typically considered healthy. |

---

### CTR – Click-Through Rate
| Field | Value |
|---|---|
| **Definition** | Percentage of users who clicked an ad after seeing it. |
| **Formula** | `CTR = Clicks / Impressions` |
| **Source Table** | `stg_marketing` |

---

### Retention Rate
| Field | Value |
|---|---|
| **Definition** | Percentage of users from an initial cohort still active after N periods. |
| **Formula** | `Retention (week N) = Active users in week N / Cohort size × 100` |
| **Source Table** | `fct_events` (cohort analysis) |

---

## 🔽 Funnel Stages

| Stage | Description |
|---|---|
| `visit` | User lands on the site/app (top of funnel) |
| `product_view` | User views a product detail page |
| `add_to_cart` | User adds an item to their cart |
| `checkout` | User initiates checkout |
| `purchase` | User completes a transaction (conversion) |

---

## 📣 Acquisition Channels

| Channel | Description |
|---|---|
| `organic_search` | Traffic from unpaid search engine results |
| `paid_search` | Traffic from PPC / SEM campaigns |
| `social_media` | Traffic from social platforms (Facebook, Instagram, etc.) |
| `email` | Traffic from email marketing campaigns |
| `referral` | Traffic from third-party links / partnerships |
| `direct` | Users typing the URL directly / bookmarks |

---

## 🎯 RFM Segments

| Segment | Definition |
|---|---|
| **Champions** | High recency, frequency, and monetary value — best customers |
| **Loyal Customers** | High recency and frequency; spend regularly |
| **Recent Customers** | Bought recently but infrequently |
| **At Risk** | Were active, but declining engagement |
| **Cannot Lose Them** | Previously high-value customers who have gone quiet |
| **Hibernating High-Value** | Low recency + frequency but high spend history |
| **Lost / Low-Value** | Inactive and low spend; difficult to re-engage |

---

## 📅 Time Dimensions

| Field | Format | Example |
|---|---|---|
| `date` | `YYYY-MM-DD` | `2025-03-15` |
| `week` | `YYYY-WNN` | `2025-W11` |
| `month` | `YYYY-MM` | `2025-03` |
| `quarter` | `YYYY-QN` | `2025-Q1` |
