import duckdb

con = duckdb.connect(
    "data/warehouse/zomato.duckdb",
    read_only=True
)

print("\n=== 1. DAILY REVENUE MODEL SUMMARY ===")
print(con.execute("""
    SELECT
        COUNT(*) AS daily_city_currency_rows,
        MIN(order_date) AS first_date,
        MAX(order_date) AS last_date,
        SUM(total_orders) AS total_orders,
        SUM(delivered_orders) AS delivered_orders,
        SUM(cancelled_orders) AS cancelled_orders,
        SUM(refunded_orders) AS refunded_orders
    FROM analytics.daily_revenue
""").fetchdf().to_string(index=False))

print("\n=== 2. TOP 10 CITIES BY DELIVERED REVENUE ===")
print(con.execute("""
    SELECT
        restaurant_city,
        currency,
        SUM(delivered_orders) AS delivered_orders,
        ROUND(SUM(delivered_revenue), 2) AS delivered_revenue
    FROM analytics.daily_revenue
    GROUP BY restaurant_city, currency
    ORDER BY delivered_revenue DESC
    LIMIT 10
""").fetchdf().to_string(index=False))

print("\n=== 3. MONTHLY DELIVERED REVENUE ===")
print(con.execute("""
    SELECT
        DATE_TRUNC('month', order_date)::DATE AS month,
        currency,
        SUM(delivered_orders) AS delivered_orders,
        ROUND(SUM(delivered_revenue), 2) AS delivered_revenue
    FROM analytics.daily_revenue
    GROUP BY month, currency
    ORDER BY month DESC, currency
    LIMIT 18
""").fetchdf().to_string(index=False))

print("\n=== 4. OVERALL REVENUE BY ORDER STATUS ===")
print(con.execute("""
    SELECT
        order_status,
        COUNT(*) AS order_count,
        ROUND(SUM(sales_amount), 2) AS recorded_sales_amount
    FROM analytics.stg_orders
    GROUP BY order_status
    ORDER BY order_count DESC
""").fetchdf().to_string(index=False))

con.close()
