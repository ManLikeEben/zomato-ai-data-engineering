from pathlib import Path
import duckdb

DB_PATH = Path("data/warehouse/zomato.duckdb")
con = duckdb.connect(str(DB_PATH))

try:
    con.execute("SET memory_limit = '3GB'")
    con.execute("SET threads = 2")

    transformations = [
        # Restaurant dimension
        """
        CREATE OR REPLACE TABLE dim_restaurant AS
        SELECT
            id AS restaurant_id,
            NULLIF(TRIM(name), '') AS restaurant_name,
            NULLIF(TRIM(city), '') AS city,
            TRY_CAST(NULLIF(TRIM(rating), '--') AS DOUBLE) AS restaurant_rating,
            TRY_CAST(
                REGEXP_EXTRACT(rating_count, '([0-9]+)', 1)
                AS BIGINT
            ) AS rating_count_estimate,
            TRY_CAST(
                NULLIF(REGEXP_REPLACE(cost, '[^0-9.]', '', 'g'), '')
                AS DOUBLE
            ) AS listed_cost,
            NULLIF(TRIM(cuisine), '') AS cuisine,
            NULLIF(TRIM(address), '') AS address
        FROM raw_restaurant
        """,

        # User dimension: safe fields only
        """
        CREATE OR REPLACE TABLE dim_user AS
        SELECT
            user_id,
            TRY_CAST("Age" AS INTEGER) AS age,
            NULLIF(TRIM("Gender"), '') AS gender,
            NULLIF(TRIM("Marital Status"), '') AS marital_status,
            NULLIF(TRIM("Occupation"), '') AS occupation,
            NULLIF(TRIM("Monthly Income"), '') AS monthly_income,
            NULLIF(TRIM("Educational Qualifications"), '') AS education,
            TRY_CAST("Family size" AS INTEGER) AS family_size
        FROM raw_users
        """,

        # Food dimension
        """
        CREATE OR REPLACE TABLE dim_food AS
        SELECT
            f_id AS food_id,
            NULLIF(TRIM(item), '') AS food_name,
            NULLIF(TRIM(veg_or_non_veg), '') AS food_type
        FROM raw_food
        """,

        # Order fact: keep identifiers as text for consistent joins
        """
        CREATE OR REPLACE TABLE fact_orders AS
        SELECT
            order_id,
            user_id,
            r_id AS restaurant_id,
            TRY_CAST(order_timestamp AS TIMESTAMP) AS order_timestamp,
            TRY_CAST(order_date AS DATE) AS order_date,
            NULLIF(TRIM(restaurant_city), '') AS restaurant_city,
            NULLIF(TRIM(cuisine), '') AS cuisine,
            TRY_CAST(items_count AS BIGINT) AS items_count,
            TRY_CAST(sales_qty AS BIGINT) AS sales_qty,
            TRY_CAST(subtotal AS DECIMAL(18,2)) AS subtotal,
            TRY_CAST(discount AS DECIMAL(18,2)) AS discount,
            TRY_CAST(delivery_fee AS DECIMAL(18,2)) AS delivery_fee,
            TRY_CAST(gst AS DECIMAL(18,2)) AS gst,
            TRY_CAST(sales_amount AS DECIMAL(18,2)) AS sales_amount,
            NULLIF(TRIM(currency), '') AS currency,
            NULLIF(TRIM(payment_method), '') AS payment_method,
            NULLIF(TRIM(order_status), '') AS order_status,
            TRY_CAST(customer_rating AS DOUBLE) AS customer_rating,
            TRY_CAST(delivery_time_min AS INTEGER) AS delivery_time_min
        FROM raw_orders
        """,

        # Order-item fact
        """
        CREATE OR REPLACE TABLE fact_order_items AS
        SELECT
            order_item_id,
            order_id,
            r_id AS restaurant_id,
            f_id AS food_id,
            TRY_CAST(price AS DECIMAL(18,2)) AS price,
            TRY_CAST(quantity AS BIGINT) AS quantity,
            TRY_CAST(line_amount AS DECIMAL(18,2)) AS line_amount
        FROM raw_order_items
        """,

        # Review fact
        """
        CREATE OR REPLACE TABLE fact_reviews AS
        SELECT
            review_id,
            order_id,
            user_id,
            restaurant_id,
            TRY_CAST(rating AS DOUBLE) AS review_rating,
            NULLIF(TRIM(comment), '') AS review_text,
            TRY_CAST(review_date AS DATE) AS review_date
        FROM raw_reviews
        """,
    ]

    for statement in transformations:
        con.execute(statement)
        table_name = statement.split("TABLE ", 1)[1].split(" AS", 1)[0]
        count = con.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()[0]
        print(f"{table_name}: {count:,} rows", flush=True)

    print("\nTransformation stage completed.")

finally:
    con.close()
