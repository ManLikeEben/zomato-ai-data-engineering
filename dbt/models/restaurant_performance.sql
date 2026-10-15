SELECT
    o.restaurant_id,
    COALESCE(
        NULLIF(TRIM(r.restaurant_name), ''),
        'Unknown restaurant'
    ) AS restaurant_name,
    COALESCE(o.restaurant_city, r.city, 'Unknown city') AS restaurant_city,
    o.currency,

    COUNT(*) AS total_orders,

    COUNT(*) FILTER (
        WHERE LOWER(TRIM(o.order_status)) = 'delivered'
    ) AS delivered_orders,

    COUNT(*) FILTER (
        WHERE LOWER(TRIM(o.order_status)) = 'cancelled'
    ) AS cancelled_orders,

    COUNT(*) FILTER (
        WHERE LOWER(TRIM(o.order_status)) = 'refunded'
    ) AS refunded_orders,

    SUM(
        CASE
            WHEN LOWER(TRIM(o.order_status)) = 'delivered'
            THEN o.sales_amount
            ELSE 0
        END
    ) AS delivered_revenue,

    AVG(
        CASE
            WHEN LOWER(TRIM(o.order_status)) = 'delivered'
            THEN o.customer_rating
        END
    ) AS avg_delivered_order_rating,

    AVG(
        CASE
            WHEN LOWER(TRIM(o.order_status)) = 'delivered'
            THEN o.delivery_time_min
        END
    ) AS avg_delivery_time_min

FROM {{ ref('stg_orders') }} o
LEFT JOIN main.dim_restaurant r
    ON o.restaurant_id = r.restaurant_id
GROUP BY
    o.restaurant_id,
    r.restaurant_name,
    COALESCE(o.restaurant_city, r.city, 'Unknown city'),
    o.currency
