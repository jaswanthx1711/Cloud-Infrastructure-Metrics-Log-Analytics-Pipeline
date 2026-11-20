{{ config(materialized='table') }}

SELECT DISTINCT
    product_id,
    CASE (CAST(REPLACE(product_id, 'PROD-', '') AS INTEGER) % 5)
        WHEN 0 THEN 'Electronics'
        WHEN 1 THEN 'Apparel'
        WHEN 2 THEN 'Home'
        WHEN 3 THEN 'Books'
        WHEN 4 THEN 'Sports'
    END AS category
FROM {{ ref('stg_sales') }}
