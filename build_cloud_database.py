from pathlib import Path
import duckdb

# ---------------------------------------------------------
# Paths and safety checks
# ---------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_DB = PROJECT_ROOT / "data" / "warehouse" / "zomato.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "data" / "cloud"
OUTPUT_DB = OUTPUT_DIR / "zomato_cloud.duckdb"

if not SOURCE_DB.is_file():
    raise FileNotFoundError(f"Source database not found: {SOURCE_DB}")

if OUTPUT_DB.exists():
    raise FileExistsError(
        f"Output database already exists: {OUTPUT_DB}\n"
        "It will NOT be overwritten. Rename or remove it deliberately "
        "only after confirming that you no longer need it."
    )

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Open source read-only. Build a completely separate destination.
source = duckdb.connect(str(SOURCE_DB), read_only=True)
target = None

try:
    print("Checking source tables...")

    required_tables = [
        "fact_orders",
        "fact_order_items",
        "fact_reviews",
        "dim_restaurant",
        "dim_food",
        "dim_user",
    ]

    available = {
        row[0]
        for row in source.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            """
        ).fetchall()
    }

    missing = set(required_tables) - available
    if missing:
        raise RuntimeError(f"Missing source tables: {sorted(missing)}")

    print("Source tables verified.")
    print("Creating separate cloud database...")

    target = duckdb.connect(str(OUTPUT_DB))

    # Attach the original warehouse as a read-only database.
    source_path_sql = str(SOURCE_DB).replace("\\", "/").replace("'", "''")

    target.execute(
        f"ATTACH '{source_path_sql}' AS source (READ_ONLY)"
    )

    # Preserve the dimensions needed for discovery and filtering.
    target.execute("""
        CREATE TABLE dim_restaurant AS
        SELECT
            restaurant_id,
            restaurant_name,
            city,
            restaurant_rating,
            rating_count_estimate,
            listed_cost,
            cuisine,
            address
        FROM source.main.dim_restaurant
    """)

    target.execute("""
        CREATE TABLE dim_food AS
        SELECT
            food_id,
            food_name,
            food_type
        FROM source.main.dim_food
    """)

    # Daily business totals by currency, city and order status.
    # Counts and sums can be combined across days for date filtering.
    target.execute("""
        CREATE TABLE agg_daily_business AS
        SELECT
            order_date,
            currency,
            restaurant_city,
            order_status,
            COUNT(*) AS order_count,
            SUM(sales_amount) AS sales_amount,
            SUM(subtotal) AS subtotal,
            SUM(discount) AS discount,
            SUM(delivery_fee) AS delivery_fee,
            SUM(gst) AS gst
        FROM source.main.fact_orders
        GROUP BY
            order_date,
            currency,
            restaurant_city,
            order_status
    """)

    # Daily restaurant performance. Store additive totals so averages
    # can be recalculated correctly across a selected date range.
    target.execute("""
        CREATE TABLE agg_daily_restaurant AS
        SELECT
            o.order_date,
            o.currency,
            o.restaurant_id,
            COUNT(*) AS order_count,
            COUNT(*) FILTER (
                WHERE o.order_status = 'Delivered'
            ) AS delivered_orders,
            COUNT(*) FILTER (
                WHERE o.order_status = 'Cancelled'
            ) AS cancelled_orders,
            COUNT(*) FILTER (
                WHERE o.order_status = 'Refunded'
            ) AS refunded_orders,
            SUM(o.sales_amount) FILTER (
                WHERE o.order_status = 'Delivered'
            ) AS delivered_revenue,
            SUM(o.customer_rating) FILTER (
                WHERE o.order_status = 'Delivered'
                  AND o.customer_rating IS NOT NULL
            ) AS rating_sum,
            COUNT(o.customer_rating) FILTER (
                WHERE o.order_status = 'Delivered'
                  AND o.customer_rating IS NOT NULL
            ) AS rating_count,
            SUM(o.delivery_time_min) FILTER (
                WHERE o.order_status = 'Delivered'
                  AND o.delivery_time_min IS NOT NULL
            ) AS delivery_time_sum,
            COUNT(o.delivery_time_min) FILTER (
                WHERE o.order_status = 'Delivered'
                  AND o.delivery_time_min IS NOT NULL
            ) AS delivery_time_count
        FROM source.main.fact_orders AS o
        GROUP BY
            o.order_date,
            o.currency,
            o.restaurant_id
    """)

    # Food sales by date and food item.
    # Join each order item to its order and food dimension before
    # aggregating. This avoids joining reviews into the same query.
    target.execute("""
        CREATE TABLE agg_daily_food AS
        SELECT
            o.order_date,
            o.currency,
            i.food_id,
            SUM(i.quantity) AS quantity_sold,
            COUNT(DISTINCT i.order_id) AS order_count,
            SUM(i.line_amount) AS item_revenue
        FROM source.main.fact_order_items AS i
        INNER JOIN source.main.fact_orders AS o
            ON i.order_id = o.order_id
        INNER JOIN source.main.dim_food AS f
            ON i.food_id = f.food_id
        WHERE o.order_status = 'Delivered'
        GROUP BY
            o.order_date,
            o.currency,
            i.food_id
    """)

    # Customer analytics at a privacy-conscious segment/date grain.
    # No individual user IDs or personal profiles are exported.
    target.execute("""
        CREATE TABLE agg_daily_customer_segments AS
        SELECT
            o.order_date,
            o.currency,
            u.gender,
            u.marital_status,
            u.occupation,
            u.education,
            u.monthly_income,
            u.family_size,
            COUNT(*) AS order_count,
            COUNT(*) FILTER (
                WHERE o.order_status = 'Delivered'
            ) AS delivered_orders,
            SUM(o.sales_amount) FILTER (
                WHERE o.order_status = 'Delivered'
            ) AS delivered_revenue,
            COUNT(DISTINCT o.user_id) AS customer_count
        FROM source.main.fact_orders AS o
        INNER JOIN source.main.dim_user AS u
            ON o.user_id = u.user_id
        GROUP BY
            o.order_date,
            o.currency,
            u.gender,
            u.marital_status,
            u.occupation,
            u.education,
            u.monthly_income,
            u.family_size
    """)

    # Review trends by date and restaurant.
    # Review text and individual user IDs are not exported.
    target.execute("""
        CREATE TABLE agg_daily_reviews AS
        SELECT
            r.review_date,
            r.restaurant_id,
            COUNT(*) AS review_count,
            SUM(r.review_rating) AS rating_sum,
            COUNT(r.review_rating) AS rating_count
        FROM source.main.fact_reviews AS r
        GROUP BY
            r.review_date,
            r.restaurant_id
    """)

    # Useful indexes for common filtering and joins.
    target.execute("""
        CREATE INDEX idx_business_date
        ON agg_daily_business(order_date)
    """)
    target.execute("""
        CREATE INDEX idx_restaurant_date
        ON agg_daily_restaurant(order_date)
    """)
    target.execute("""
        CREATE INDEX idx_food_date
        ON agg_daily_food(order_date)
    """)

    print("\nValidating generated database...")

    source_orders = target.execute("""
    SELECT COUNT(*) FROM source.main.fact_orders
""").fetchone()[0]

    source_delivered = target.execute("""
        SELECT COUNT(*)
        FROM source.main.fact_orders
        WHERE order_status = 'Delivered'
    """).fetchone()[0]

    cloud_orders = target.execute("""
        SELECT SUM(order_count)
        FROM agg_daily_business
    """).fetchone()[0]

    cloud_delivered = target.execute("""
        SELECT SUM(order_count)
        FROM agg_daily_business
        WHERE order_status = 'Delivered'
    """).fetchone()[0]

    checks = {
        "Total orders": (source_orders, cloud_orders),
        "Delivered orders": (source_delivered, cloud_delivered),
    }

    for label, (expected, actual) in checks.items():
        print(f"{label}: source={expected:,}, cloud={actual:,}")
        if expected != actual:
            raise RuntimeError(
                f"Validation failed for {label}: "
                f"source={expected}, cloud={actual}"
            )

    tables = [
        "dim_restaurant",
        "dim_food",
        "agg_daily_business",
        "agg_daily_restaurant",
        "agg_daily_food",
        "agg_daily_customer_segments",
        "agg_daily_reviews",
    ]

    print("\nCloud table row counts:")
    for table in tables:
        count = target.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]
        print(f"  {table}: {count:,}")

    target.execute("CHECKPOINT")
    target.close()
    target = None

    size_mb = OUTPUT_DB.stat().st_size / (1024 * 1024)

    print("\nSUCCESS: Cloud database created.")
    print(f"Location: {OUTPUT_DB}")
    print(f"File size: {size_mb:,.2f} MB")
    print("Original warehouse was opened read-only.")

except Exception:
    if target is not None:
        target.close()
        target = None

    # Remove only this script's incomplete output after a failure.
    # The source database is never modified.
    if OUTPUT_DB.exists():
        OUTPUT_DB.unlink()

    raise

finally:
    source.close()