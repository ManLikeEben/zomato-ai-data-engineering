import time
import os
import re
import requests
import sqlglot

from dotenv import load_dotenv
from sqlglot import exp

load_dotenv()

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen2.5:1.5b"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-3.1-flash-lite"

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _post_with_retry(
    url,
    *,
    headers,
    payload,
    timeout,
    max_attempts=3,
):
    """Retry requests after temporary HTTP, connection, or timeout errors."""

    for attempt in range(max_attempts):
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout,
            )

            if response.status_code in RETRYABLE_STATUS_CODES:
                if attempt < max_attempts - 1:
                    print(
                        f"AI service returned HTTP {response.status_code}. "
                        f"Retrying attempt {attempt + 2}/{max_attempts}."
                    )
                    time.sleep(2 ** attempt)
                    continue

            if not response.ok:
                print("AI HTTP status:", response.status_code)
                print("AI error details:", response.text[:2000])
                response.raise_for_status()

            return response

        except (requests.ConnectionError, requests.Timeout):
            if attempt == max_attempts - 1:
                raise

            print(
                f"AI connection failed. "
                f"Retrying attempt {attempt + 2}/{max_attempts}."
            )
            time.sleep(2 ** attempt)

    raise RuntimeError("AI request failed after all retry attempts.")



DATABASE_SCHEMA = """
You are EBEN, a Text-to-SQL assistant for a Zomato analytics database.

DATABASE CONTEXT
The application uses a read-only DuckDB cloud analytics database.
The database contains pre-aggregated analytics tables and dimensions.
Do not assume that the original raw fact tables are available.

APPROVED TABLES AND COLUMNS

1. main.agg_daily_business
   Columns:
   order_date, currency, restaurant_city, order_status,
   order_count, sales_amount, subtotal, discount, delivery_fee, gst

   Purpose:
   Daily business metrics by date, currency, city and order status.

2. main.agg_daily_restaurant
   Columns:
   order_date, currency, restaurant_id, order_count,
   delivered_orders, cancelled_orders, refunded_orders,
   delivered_revenue, rating_sum, rating_count,
   delivery_time_sum, delivery_time_count

   Purpose:
   Daily restaurant-level performance metrics.

3. main.agg_daily_food
   Columns:
   order_date, currency, food_id, quantity_sold,
   order_count, item_revenue

   Purpose:
   Daily food sales and quantity metrics.

4. main.agg_daily_customer_segments
   Columns:
   order_date, currency, gender, marital_status, occupation,
   education, monthly_income, family_size, order_count,
   delivered_orders, delivered_revenue, customer_count

   Purpose:
   Daily aggregated customer-segment metrics.
   Do not claim that SUM(customer_count) represents unique
   customers over a date range. It represents summed daily counts.

5. main.agg_daily_reviews
   Columns:
   review_date, restaurant_id, review_count, rating_sum, rating_count

   Purpose:
   Daily aggregated review metrics.

6. main.dim_restaurant
   Columns:
   restaurant_id, restaurant_name, city, restaurant_rating,
   rating_count_estimate, listed_cost, cuisine, address

   Purpose:
   Restaurant descriptive information.

7. main.dim_food
   Columns:
   food_id, food_name, food_type

   Purpose:
   Food descriptive information.

IMPORTANT BUSINESS RULES

- Generate DuckDB-compatible SQL.
- Return exactly one read-only SELECT query.
- Do not use CTEs or WITH clauses.
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE,
  COPY, ATTACH, or DETACH statements.
- Query only the approved tables listed above.
- Never reference the original raw fact tables.
- Never invent table or column names.
- Use the correct columns for each table.
- Filter currency when comparing or reporting financial values.
- Use SUM(order_count) for total orders across aggregated rows.
- Use SUM(order_count) with order_status = 'Delivered'
  for delivered orders from agg_daily_business.
- Use SUM(order_count) with order_status = 'Cancelled'
  for cancelled orders from agg_daily_business.
- Use SUM(order_count) with order_status = 'Refunded'
  for refunded orders from agg_daily_business.
- For delivered revenue from agg_daily_business, use
  SUM(sales_amount) and filter order_status = 'Delivered'.
- For delivered revenue from agg_daily_restaurant, use
  SUM(delivered_revenue).
- Do not sum sales_amount across all statuses when the question
  asks for delivered revenue.
- For a month, filter from the first day inclusive to the first
  day of the following month exclusive.
- For "top N", use LIMIT N.
- Use LIMIT 100 for questions without a smaller requested limit.
- For revenue by city, use restaurant_city from agg_daily_business.
- For restaurant names and descriptive information, join
  agg_daily_restaurant to dim_restaurant using restaurant_id.
- Do not join independent aggregate tables unless the question
  requires it. Joining aggregates can multiply values.
- Never access private user contact information.
- Return only SQL, without Markdown or explanations.

EXAMPLES

Question: What are the total orders, delivered orders and
delivered revenue for INR?

SELECT
    SUM(order_count) AS total_orders,
    SUM(CASE WHEN order_status = 'Delivered'
        THEN order_count ELSE 0 END) AS delivered_orders,
    SUM(CASE WHEN order_status = 'Delivered'
        THEN sales_amount ELSE 0 END) AS delivered_revenue
FROM main.agg_daily_business
WHERE currency = 'INR'

Question: What are the top 5 cities by delivered revenue in INR?

SELECT
    restaurant_city,
    SUM(sales_amount) AS delivered_revenue
FROM main.agg_daily_business
WHERE order_status = 'Delivered'
  AND currency = 'INR'
GROUP BY restaurant_city
ORDER BY delivered_revenue DESC
LIMIT 5

Question: How many orders were cancelled in January 2026?

SELECT
    SUM(order_count) AS cancelled_orders
FROM main.agg_daily_business
WHERE order_status = 'Cancelled'
  AND order_date >= DATE '2026-01-01'
  AND order_date < DATE '2026-02-01'
  AND currency = 'INR'

Question: What are the top 10 restaurants by delivered revenue in INR?

SELECT
    r.restaurant_id,
    r.restaurant_name,
    SUM(a.delivered_revenue) AS delivered_revenue
FROM main.agg_daily_restaurant AS a
JOIN main.dim_restaurant AS r
    ON a.restaurant_id = r.restaurant_id
WHERE a.currency = 'INR'
GROUP BY r.restaurant_id, r.restaurant_name
HAVING SUM(a.delivered_orders) > 0
ORDER BY delivered_revenue DESC
LIMIT 10
"""

ALLOWED_TABLES = {
    "main.agg_daily_business",
    "main.agg_daily_restaurant",
    "main.agg_daily_food",
    "main.agg_daily_customer_segments",
    "main.agg_daily_reviews",
    "main.dim_restaurant",
    "main.dim_food",
}


def generate_sql(
    question: str,
    error_feedback: str | None = None,
) -> str:
    """Generate and validate DuckDB SQL using Ollama or Gemini."""

    if not question or not question.strip():
        raise ValueError("Please enter a question.")

    if AI_PROVIDER == "ollama":
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": DATABASE_SCHEMA,
                },
                {
                    "role": "user",
                    "content": (
                        f"Question: {question.strip()}"
                        if not error_feedback
                        else (
                            f"Question: {question.strip()}\n\n"
                            f"Previous SQL error: {error_feedback}\n\n"
                            "Correct the SQL. Return one DuckDB SELECT "
                            "query only, without Markdown."
                        )
                    ),
                },
            ],
            "stream": False,
            "options": {"temperature": 0},
        }

        response = _post_with_retry(
            OLLAMA_URL,
            headers={"Content-Type": "application/json"},
            payload=payload,
            timeout=120,
        )

        try:
            sql = response.json()["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(
                "Ollama did not return SQL text."
            ) from error

    elif AI_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is missing. Configure it in your "
                ".env file locally or Streamlit secrets in the cloud."
            )

        gemini_url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_MODEL}:generateContent"
        )

        user_prompt = f"Question: {question.strip()}"

        if error_feedback:
            user_prompt += (
                f"\n\nThe previous SQL query failed with this error:\n"
                f"{error_feedback}\n\n"
                "Correct the SQL using the error information. "
                "Return one DuckDB SELECT query only, without Markdown."
            )

        payload = {
            "system_instruction": {
                "parts": [{"text": DATABASE_SCHEMA}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "thinkingConfig": {"thinkingLevel": "low"},
                "maxOutputTokens": 1024,
            },
        }

        response = _post_with_retry(
            gemini_url,
            headers={
                "x-goog-api-key": GEMINI_API_KEY,
                "Content-Type": "application/json",
            },
            payload=payload,
            timeout=120,
        )

        try:
            sql = (
                response.json()["candidates"][0]["content"]["parts"][0]["text"]
                .strip()
            )
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(
                "Gemini did not return SQL text. Check the API response "
                "and try again."
            ) from error

    else:
        raise ValueError(
            f"Unsupported AI_PROVIDER: {AI_PROVIDER}. "
            "Choose 'ollama' or 'gemini'."
        )

    # Remove Markdown fences if the model adds them.
    sql = re.sub(
        r"^```(?:sql)?\s*",
        "",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(r"\s*```$", "", sql).strip()

    # Preserve the existing SQL security checks.
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