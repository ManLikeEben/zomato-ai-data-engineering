import sqlglot
from sqlglot import exp
import re

import requests


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:1.5b"


DATABASE_SCHEMA = """
You are a Text-to-SQL assistant for a Zomato analytics database.

You may query ONLY these approved tables:

1. main.fact_orders
   Columns:
   order_id, user_id, restaurant_id, order_timestamp,
   order_date, restaurant_city, cuisine, items_count,
   sales_qty, subtotal, discount, delivery_fee, gst,
   sales_amount, currency, payment_method, order_status,
   customer_rating, delivery_time_min

2. main.dim_restaurant
   Columns:
   restaurant_id, restaurant_name, city, restaurant_rating,
   rating_count_estimate, listed_cost, cuisine, address

3. main.dim_user
   Columns:
   user_id, age, gender, marital_status, occupation,
   monthly_income, education, family_size

4. main.dim_food
   Columns:
   food_id, food_name, food_type

5. main.fact_order_items
   Columns:
   order_item_id, order_id, restaurant_id, food_id,
   price, quantity, line_amount

6. main.fact_reviews
   Columns:
   review_id, order_id, user_id, restaurant_id,
   review_rating, review_text, review_date
EXAMPLES OF CORRECT SQL:

Question: What are the top 5 cities by delivered revenue?

SELECT
    restaurant_city,
    SUM(sales_amount) AS delivered_revenue
FROM main.fact_orders
WHERE order_status = 'Delivered'
GROUP BY restaurant_city
ORDER BY delivered_revenue DESC
LIMIT 5

Question: How many orders were cancelled in January 2026?

SELECT COUNT(*) AS cancelled_orders
FROM main.fact_orders
WHERE order_status = 'Cancelled'
  AND order_date >= DATE '2026-01-01'
  AND order_date < DATE '2026-02-01'

Question: What are the top 10 restaurants by delivered revenue?

SELECT
    r.restaurant_id,
    r.restaurant_name,
    SUM(o.sales_amount) AS delivered_revenue
FROM main.fact_orders AS o
JOIN main.dim_restaurant AS r
    ON o.restaurant_id = r.restaurant_id
WHERE o.order_status = 'Delivered'
GROUP BY r.restaurant_id, r.restaurant_name
ORDER BY delivered_revenue DESC
LIMIT 10

Rules:
- Generate DuckDB-compatible SQL.
- Return exactly one read-only SELECT query.
- Do not use CTEs or WITH clauses.
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE,
  COPY, ATTACH, or DETACH statements.
- Never access tables outside the approved list.
- Never access private user contact information.
- Never invent column names.
- For delivered revenue, use sales_amount and filter
  order_status = 'Delivered'.
- Cancelled orders must use order_status = 'Cancelled'.
- Refunded orders must use order_status = 'Refunded'.
- For a month, filter from the first day of the month inclusive
  to the first day of the next month exclusive.
- For "top N", use LIMIT N, not LIMIT 100.
- Use LIMIT 100 for questions without a smaller requested limit.
- Return only SQL, without Markdown or explanations.
- IMPORTANT: main.fact_orders has a column named restaurant_city.
- IMPORTANT: main.dim_restaurant has a column named city,
  NOT restaurant_city.
- Never reference a column under a table alias unless that
  column exists in that table.
- For questions about revenue by city, use restaurant_city
  from main.fact_orders and do not join dim_restaurant.
- Only join tables when the question requires columns from
  multiple tables.
- For top 5 cities by delivered revenue, use this exact query:

SELECT restaurant_city,
       SUM(sales_amount) AS delivered_revenue
FROM main.fact_orders
WHERE order_status = 'Delivered'
GROUP BY restaurant_city
ORDER BY delivered_revenue DESC
LIMIT 5
"""


ALLOWED_TABLES = {
    "main.fact_orders",
    "main.dim_restaurant",
    "main.dim_user",
    "main.dim_food",
    "main.fact_order_items",
    "main.fact_reviews",
}


def generate_sql(
    question: str,
    error_feedback: str | None = None,
) -> str:
    """Generate and validate DuckDB SQL using local Ollama."""

    if not question or not question.strip():
        raise ValueError("Please enter a question.")

    messages = [
        {
            "role": "system",
            "content": DATABASE_SCHEMA,
        },
        {
            "role": "user",
            "content": question.strip(),
        },
    ]

    # If a previous query failed, ask the model to correct it.
    if error_feedback:
        messages.append(
            {
                "role": "user",
                "content": (
                    "Your previous SQL query failed. Correct it using "
                    "the error information below.\n\n"
                    f"{error_feedback}\n\n"
                    "Generate a corrected DuckDB SELECT query. "
                    "Use only approved tables and existing columns. "
                    "Return SQL only, without Markdown or explanations."
                ),
            }
        )

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0,
            },
        },
        timeout=180,
    )

    response.raise_for_status()

    sql = response.json()["message"]["content"].strip()

    # Remove Markdown fences if the model adds them.
    sql = re.sub(
        r"^```(?:sql)?\s*",
        "",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(r"\s*```$", "", sql).strip()

    # Validate before returning anything to the execution layer.
    sql = validate_sql(sql)

    return sql

def validate_sql(sql: str) -> str:
    """Parse and validate a single read-only DuckDB query."""

    cleaned_sql = sql.strip()

    # Parse the SQL using DuckDB's dialect.
    try:
        statements = sqlglot.parse(cleaned_sql, read="duckdb")
    except sqlglot.errors.ParseError as error:
        raise ValueError("The generated SQL is invalid.") from error

    # Exactly one statement is allowed.
    if len(statements) != 1 or statements[0] is None:
        raise ValueError("Only one SQL statement is allowed.")

    tree = statements[0]

    # Only SELECT queries are allowed.
    if not isinstance(tree, exp.Select):
        raise ValueError("Only SELECT queries are allowed.")

    # Reject external table functions and other table sources.
    for node in tree.walk():
        if isinstance(node, exp.Table):
            if node.catalog or node.db != "main":
                raise ValueError(
                    "Only approved tables in the main schema are allowed."
                )

            table_name = node.name.lower()
            full_name = f"main.{table_name}"

            if full_name not in ALLOWED_TABLES:
                raise ValueError(
                    f"Table is not approved: {full_name}"
                )

        # Disallow SELECT INTO and other non-read-only constructs.
        if isinstance(node, exp.Into):
            raise ValueError("SELECT INTO is not allowed.")

    # Bound the returned rows.
    limit = tree.args.get("limit")

    if limit is None:
        tree = tree.limit(100)
    else:
        limit_value = limit.expression

        if not isinstance(limit_value, exp.Literal) or limit_value.is_string:
            raise ValueError("LIMIT must be a numeric constant.")

        try:
            number = int(limit_value.this)
        except (TypeError, ValueError) as error:
            raise ValueError("LIMIT must be a numeric constant.") from error

        if number < 1:
            raise ValueError("LIMIT must be at least 1.")

        if number > 100:
            tree = tree.limit(100)

    return tree.sql(dialect="duckdb")