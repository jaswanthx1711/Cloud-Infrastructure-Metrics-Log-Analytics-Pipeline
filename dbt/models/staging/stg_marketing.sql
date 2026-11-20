{{ config(materialized='view') }}

SELECT
    campaign_id,
    campaign_name,
    channel,
    DATE(start_date)                            AS start_date,
    DATE(end_date)                              AS end_date,
    budget,
    spend,
    impressions,
    clicks,
    conversions,
    revenue_attributed,
    ROUND(1.0 * clicks / NULLIF(impressions, 0),    4) AS ctr,
    ROUND(1.0 * conversions / NULLIF(clicks, 0),    4) AS cvr,
    ROUND(spend / NULLIF(conversions, 0),           2) AS cac,
    ROUND(revenue_attributed / NULLIF(spend, 0),    2) AS roas
FROM {{ source('bronze', 'raw_marketing') }}
