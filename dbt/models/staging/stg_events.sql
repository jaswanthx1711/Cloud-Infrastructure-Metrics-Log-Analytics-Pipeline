{{ config(materialized='view') }}

SELECT
    event_id,
    user_id,
    session_id,
    stage,
    CASE stage
        WHEN 'visit'         THEN 1
        WHEN 'product_view'  THEN 2
        WHEN 'add_to_cart'   THEN 3
        WHEN 'checkout'      THEN 4
        WHEN 'purchase'      THEN 5
    END                              AS stage_order,
    product_id,
    timestamp,
    DATE(timestamp)                  AS date,
    STRFTIME('%Y-W%W', timestamp)    AS week,
    STRFTIME('%Y-%m', timestamp)     AS month,
    device,
    country
FROM {{ source('bronze', 'raw_user_events') }}
GROUP BY event_id
