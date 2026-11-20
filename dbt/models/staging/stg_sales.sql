{{ config(materialized='view') }}

SELECT
    order_id,
    line_id,
    user_id,
    product_id,
    quantity,
    unit_price,
    discount_pct,
    ROUND(unit_price * quantity * (1.0 - discount_pct / 100.0), 2) AS net_revenue,
    DATE(order_date)                 AS order_date,
    STRFTIME('%Y-%m', order_date)    AS month,
    CASE
        WHEN CAST(STRFTIME('%m', order_date) AS INTEGER) BETWEEN 1  AND 3  THEN STRFTIME('%Y', order_date) || '-Q1'
        WHEN CAST(STRFTIME('%m', order_date) AS INTEGER) BETWEEN 4  AND 6  THEN STRFTIME('%Y', order_date) || '-Q2'
        WHEN CAST(STRFTIME('%m', order_date) AS INTEGER) BETWEEN 7  AND 9  THEN STRFTIME('%Y', order_date) || '-Q3'
        ELSE                                                                     STRFTIME('%Y', order_date) || '-Q4'
    END                              AS quarter,
    status,
    channel,
    country
FROM {{ source('bronze', 'raw_sales') }}
