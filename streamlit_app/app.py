import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
import pandas as pd
import streamlit as st
from huggingface_hub import hf_hub_download


# --------------------------------------------------
# AI configuration
# --------------------------------------------------

# Read the Gemini key from Streamlit Cloud Secrets when available.
try:
    cloud_api_key = st.secrets["GEMINI_API_KEY"]
except (KeyError, FileNotFoundError):
    cloud_api_key = None

if cloud_api_key:
    os.environ["GEMINI_API_KEY"] = cloud_api_key
    os.environ["AI_PROVIDER"] = "gemini"


# Import AI services only after configuring the environment.
from src.text_to_sql.execution_service import execute_query
from src.text_to_sql.summary_service import summarize_result

# --------------------------------------------------
# Configuration
# --------------------------------------------------

# Original warehouse: preserved and not modified.
LOCAL_DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "warehouse"
    / "zomato.duckdb"
)

# Smaller database prepared for the dashboard and cloud deployment.
LOCAL_CLOUD_DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "cloud"
    / "zomato_cloud.duckdb"
)

# Public Hugging Face dataset used when deploying to the cloud.
HF_REPO_ID = "TheHelpedOne/zomato-cloud-analytics"
HF_DB_FILENAME = "zomato_cloud.duckdb"

st.set_page_config(
    page_title="Zomato Analytics",
    page_icon="🍽️",
    layout="wide",
)


# --------------------------------------------------
# Database connection
# --------------------------------------------------

@st.cache_resource
def get_connection():
    # Prefer the prepared cloud database when available locally.
    if LOCAL_CLOUD_DB_PATH.exists():
        db_path = LOCAL_CLOUD_DB_PATH

    # Otherwise, download the prepared database from Hugging Face.
    else:
        db_path = hf_hub_download(
            repo_id=HF_REPO_ID,
            filename=HF_DB_FILENAME,
            repo_type="dataset",
        )

    # Open the database in read-only mode.
    return duckdb.connect(str(db_path), read_only=True)


# --------------------------------------------------
# Data loading
# --------------------------------------------------

@st.cache_data(ttl=300)
def load_data(query, params=()):
    connection = get_connection()
    return connection.execute(query, params).fetchdf()


# --------------------------------------------------
# Dashboard header
# --------------------------------------------------

st.title("🍽️ Zomato Analytics Dashboard")

st.markdown(
    """
    Explore order performance, delivered revenue,
    restaurant activity and city-level trends.
    """
)

st.caption("Data warehouse: DuckDB | Analytics: SQL and Python")


# --------------------------------------------------
# Currency filter
# --------------------------------------------------

currencies = load_data(
    """
    SELECT DISTINCT currency
    FROM main.agg_daily_business
    WHERE currency IS NOT NULL
    ORDER BY currency
    """
)

currency_options = currencies["currency"].tolist()

if not currency_options:
    st.error("No currencies were found in the analytics database.")
    st.stop()

selected_currency = st.selectbox(
    "Select currency",
    currency_options,
)

st.caption(f"All financial figures are displayed in {selected_currency}.")


# --------------------------------------------------
# Date filters
# --------------------------------------------------

date_range = load_data(
    """
    SELECT
        MIN(order_date) AS min_date,
        MAX(order_date) AS max_date
    FROM main.agg_daily_business
    WHERE currency = ?
    """,
    (selected_currency,),
)

min_date = pd.to_datetime(date_range.iloc[0]["min_date"]).date()
max_date = pd.to_datetime(date_range.iloc[0]["max_date"]).date()

st.subheader("Filter by Date")

col1, col2 = st.columns(2)

with col1:
    start_date = st.date_input(
        "Start date",
        value=min_date,
        min_value=min_date,
        max_value=max_date,
    )

with col2:
    end_date = st.date_input(
        "End date",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
    )

if start_date > end_date:
    st.error("The start date cannot be later than the end date.")
    st.stop()


# --------------------------------------------------
# Load summary metrics
# --------------------------------------------------

try:
    summary = load_data(
        """
        SELECT
            SUM(order_count) AS total_orders,
            SUM(order_count) FILTER (
                WHERE order_status = 'Delivered'
            ) AS delivered_orders,
            SUM(order_count) FILTER (
                WHERE order_status = 'Cancelled'
            ) AS cancelled_orders,
            SUM(order_count) FILTER (
                WHERE order_status = 'Refunded'
            ) AS refunded_orders,
            SUM(sales_amount) FILTER (
                WHERE order_status = 'Delivered'
            ) AS delivered_revenue
        FROM main.agg_daily_business
        WHERE currency = ?
          AND order_date BETWEEN ? AND ?
        """,
        (selected_currency, start_date, end_date),
    )

    metrics = summary.iloc[0]

    total_orders = int(metrics["total_orders"] or 0)
    delivered_orders = int(metrics["delivered_orders"] or 0)
    cancelled_orders = int(metrics["cancelled_orders"] or 0)
    refunded_orders = int(metrics["refunded_orders"] or 0)
    delivered_revenue = float(metrics["delivered_revenue"] or 0)

    # --------------------------------------------------
    # Key performance indicators
    # --------------------------------------------------

    st.subheader("Business Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Orders", f"{total_orders:,}")

    col2.metric(
        "Delivered Orders",
        f"{delivered_orders:,}",
        f"{delivered_orders / total_orders:.1%} of orders"
        if total_orders else "0% of orders",
    )

    col3.metric(
        "Cancelled Orders",
        f"{cancelled_orders:,}",
        f"{cancelled_orders / total_orders:.1%} of orders"
        if total_orders else "0% of orders",
    )

    col4.metric(
        "Delivered Revenue",
        f"{selected_currency} {delivered_revenue:,.0f}",
    )

    st.caption(
        f"Refunded orders: {refunded_orders:,}. "
        "Revenue includes delivered orders only."
    )

    st.divider()

    # --------------------------------------------------
    # Monthly revenue
    # --------------------------------------------------

    st.subheader("Monthly Delivered Revenue")

    monthly_revenue = load_data(
        """
        SELECT
            DATE_TRUNC('month', order_date) AS month,
            SUM(sales_amount) AS delivered_revenue
        FROM main.agg_daily_business
        WHERE order_status = 'Delivered'
          AND currency = ?
          AND order_date BETWEEN ? AND ?
        GROUP BY 1
        ORDER BY 1
        """,
        (selected_currency, start_date, end_date),
    )

    if not monthly_revenue.empty:
        monthly_revenue["month"] = pd.to_datetime(
            monthly_revenue["month"]
        )

        st.line_chart(
            monthly_revenue.set_index("month")["delivered_revenue"],
            y_label=f"Revenue ({selected_currency})",
        )
    else:
        st.info("No monthly revenue data is available for this date range.")

    # --------------------------------------------------
    # Top cities
    # --------------------------------------------------

    st.subheader("Top 10 Cities by Delivered Revenue")

    top_cities = load_data(
        """
        SELECT
            restaurant_city AS city,
            SUM(order_count) AS delivered_orders,
            SUM(sales_amount) AS delivered_revenue
        FROM main.agg_daily_business
        WHERE order_status = 'Delivered'
          AND currency = ?
          AND order_date BETWEEN ? AND ?
        GROUP BY restaurant_city
        ORDER BY delivered_revenue DESC
        LIMIT 10
        """,
        (selected_currency, start_date, end_date),
    )

    if not top_cities.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.bar_chart(
                top_cities.set_index("city")["delivered_revenue"],
                horizontal=True,
                x_label=f"Revenue ({selected_currency})",
            )

        with col2:
            st.dataframe(
                top_cities,
                hide_index=True,
                use_container_width=True,
            )
    else:
        st.info("No city data is available for this date range.")

    # --------------------------------------------------
    # Restaurant Performance
    # --------------------------------------------------

    st.divider()
    st.subheader("Restaurant Performance")

    restaurant_performance = load_data(
        """
        SELECT
            r.restaurant_name,
            r.city,
            SUM(a.delivered_orders) AS delivered_orders,
            SUM(a.delivered_revenue) AS delivered_revenue,
            ROUND(
                SUM(a.rating_sum) /
                NULLIF(SUM(a.rating_count), 0),
                2
            ) AS average_customer_rating,
            ROUND(
                SUM(a.delivery_time_sum) /
                NULLIF(SUM(a.delivery_time_count), 0),
                1
            ) AS average_delivery_minutes
        FROM main.agg_daily_restaurant AS a
        LEFT JOIN main.dim_restaurant AS r
            ON a.restaurant_id = r.restaurant_id
        WHERE a.currency = ?
          AND a.order_date BETWEEN ? AND ?
        GROUP BY r.restaurant_name, r.city
        HAVING SUM(a.delivered_orders) > 0
        ORDER BY delivered_revenue DESC
        LIMIT 20
        """,
        (selected_currency, start_date, end_date),
    )

    if not restaurant_performance.empty:
        st.caption(
            "Top 20 restaurants ranked by delivered revenue "
            "for your selected currency and date range."
        )

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Top Restaurants by Revenue**")
            st.bar_chart(
                restaurant_performance.head(10).set_index(
                    "restaurant_name"
                )["delivered_revenue"],
                horizontal=True,
                x_label=f"Revenue ({selected_currency})",
            )

        with col2:
            st.markdown("**Restaurant Performance Details**")
            st.dataframe(
                restaurant_performance,
                hide_index=True,
                use_container_width=True,
            )
    else:
        st.info("No restaurant data is available for this date range.")

    # --------------------------------------------------
    # Order Status Analysis
    # --------------------------------------------------

    st.divider()
    st.subheader("Order Status Analysis")

    order_status_data = load_data(
        """
        SELECT
            order_status,
            SUM(order_count) AS order_count,
            ROUND(
                SUM(order_count) * 100.0 /
                NULLIF(SUM(SUM(order_count)) OVER (), 0),
                2
            ) AS percentage
        FROM main.agg_daily_business
        WHERE currency = ?
          AND order_date BETWEEN ? AND ?
        GROUP BY order_status
        ORDER BY order_count DESC
        """,
        (selected_currency, start_date, end_date),
    )

    if not order_status_data.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Order Distribution**")
            st.bar_chart(
                order_status_data.set_index("order_status")["order_count"],
                x_label="Order Status",
                y_label="Number of Orders",
            )

        with col2:
            st.markdown("**Status Breakdown**")
            st.dataframe(
                order_status_data,
                hide_index=True,
                use_container_width=True,
            )
    else:
        st.info("No order status data is available for this date range.")

    # --------------------------------------------------
    # Interactive Restaurant Explorer
    # --------------------------------------------------

    st.divider()
    st.subheader("🔎 Restaurant Explorer")

    restaurant_filters = load_data(
        """
        SELECT DISTINCT city
        FROM main.dim_restaurant
        WHERE city IS NOT NULL
        ORDER BY city
        """
    )

    city_options = ["All Cities"] + restaurant_filters["city"].tolist()

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        restaurant_search = st.text_input(
            "Search restaurant name",
            placeholder="e.g. Theobroma",
        )

    with col2:
        selected_city = st.selectbox("Filter by city", city_options)

    with col3:
        minimum_rating = st.slider(
            "Minimum rating",
            min_value=0.0,
            max_value=5.0,
            value=0.0,
            step=0.5,
        )

    restaurant_results = load_data(
        """
        SELECT
            r.restaurant_name,
            r.city,
            r.restaurant_rating,
            r.rating_count_estimate,
            r.listed_cost,
            r.cuisine
        FROM main.dim_restaurant AS r
        WHERE
            (? = '' OR LOWER(r.restaurant_name) LIKE '%' || LOWER(?) || '%')
            AND (? = 'All Cities' OR r.city = ?)
            AND COALESCE(r.restaurant_rating, 0) >= ?
        ORDER BY r.restaurant_rating DESC NULLS LAST
        LIMIT 100
        """,
        (
            restaurant_search,
            restaurant_search,
            selected_city,
            selected_city,
            minimum_rating,
        ),
    )

    st.caption(
        f"Showing {len(restaurant_results):,} matching restaurants "
        "(maximum 100 results)."
    )

    st.dataframe(
        restaurant_results,
        hide_index=True,
        use_container_width=True,
    )

except Exception as error:
    st.error("The dashboard could not load the warehouse data.")
    st.exception(error)
# ==========================================
# EBEN: AI-Powered Natural Language Queries
# ==========================================

st.divider()

st.header("🤖 Ask EBEN")

st.caption(
    "Hi, I'm EBEN, your Enhanced Being for Exploration and Navigation. "
    "Ask me anything about your Zomato data in plain English."
)

# Initialise conversation memory.
if "eben_history" not in st.session_state:
    st.session_state.eben_history = []

if "eben_last_question" not in st.session_state:
    st.session_state.eben_last_question = None

if "eben_last_result" not in st.session_state:
    st.session_state.eben_last_result = None

if "eben_last_sql" not in st.session_state:
    st.session_state.eben_last_sql = None

question = st.text_input(
    "What would you like to know?",
    placeholder="e.g. What are the top 5 cities by delivered revenue?",
    key="eben_question",
)

col1, col2 = st.columns([3, 1])

with col1:
    ask_button = st.button("Ask EBEN", type="primary")

with col2:
    clear_button = st.button("Clear Memory")


# Clear stored conversation.
if clear_button:
    st.session_state.eben_history = []
    st.session_state.eben_last_question = None
    st.session_state.eben_last_result = None
    st.session_state.eben_last_sql = None

    st.rerun()


if ask_button:

    if not question.strip():
        st.warning("Please enter a question first.")

    else:
        lower_question = question.strip().lower()

        previous_result = st.session_state.eben_last_result

        # Recognise ordinal references to previous results.
        ordinal_phrases = {
            "first": 0,
            "second": 1,
            "third": 2,
            "fourth": 3,
            "fifth": 4,
        }

        selected_index = None

        for ordinal, index in ordinal_phrases.items():
            if (
                f"{ordinal} one" in lower_question
                or f"{ordinal} result" in lower_question
                or lower_question.strip() == ordinal
            ):
                selected_index = index
                break
            # Detect ordinal follow-ups even when memory is empty.
        ordinal_follow_up = selected_index is not None

        if ordinal_follow_up and (
            st.session_state.eben_last_result is None
            or st.session_state.eben_last_result.empty
        ):
            st.warning(
                "I don't have a previous result to refer to. "
                "Please ask a new question first."
            )
            st.stop()


        is_follow_up = (
            previous_result is not None
            and not previous_result.empty
            and selected_index is not None
        )

        try:
            if is_follow_up:
                # Select the previous result directly in Python.
                if selected_index >= len(previous_result):
                    st.warning(
                        "That result isn't available in the previous answer."
                    )

                else:
                    selected_row = previous_result.iloc[selected_index]

                    st.subheader("EBEN's Answer")

                    # Identify the selected result.
                    columns = {
                        column.lower(): column
                        for column in selected_row.index
                    }

                    location_col = next(
                        (
                            columns[name]
                            for name in [
                                "restaurant_city",
                                "restaurant_name",
                                "city",
                                "name",
                            ]
                            if name in columns
                        ),
                        None,
                    )

                    revenue_col = next(
                        (
                            columns[name]
                            for name in [
                                "delivered_revenue",
                                "total_revenue",
                                "revenue",
                            ]
                            if name in columns
                        ),
                        None,
                    )

                    if location_col and revenue_col:
                        location = selected_row[location_col]
                        revenue = float(selected_row[revenue_col])

                        st.success(
                            f"Result number {selected_index + 1} is "
                            f"**{location}**, with revenue of "
                            f"**₹{revenue:,.2f}**."
                        )

                    elif location_col:
                        location = str(selected_row[location_col]).replace(",", ", ").replace(",  ", ", ")
                        st.success(
                            f"Result number {selected_index + 1} is "
                            f"**{location}**."
                        )

                    else:
                        st.write(
                            f"Here is result number "
                            f"{selected_index + 1} from your previous query:"
                        )

                    with st.expander("View complete result"):
                        st.dataframe(
                            selected_row.to_frame().T,
                            use_container_width=True,
                            hide_index=True,
                        )
                    st.caption(
                        "This result was retrieved from the previous query. "
                        "No new SQL query was executed."
                    )

                    # Preserve the original results so further ordinal
                    # references still use the original result set.
                    st.session_state.eben_history.append(
                        {
                            "question": question.strip(),
                            "summary": (
                                f"Displayed result number "
                                f"{selected_index + 1} from the previous query."
                            ),
                        }
                    )

            else:
                # Run a new natural-language query.
                with st.spinner(
                    "EBEN is analysing your question and querying the warehouse..."
                ):
                    generated_sql, query_result = execute_query(
                        question.strip()
                    )

                st.subheader("EBEN's Summary")

                summary = summarize_result(
                    question,
                    query_result,
                )

                st.info(summary)

                st.subheader("Query Results")

                if query_result.empty:
                    st.info("No results found for your question.")

                else:
                    st.dataframe(
                        query_result,
                        use_container_width=True,
                        hide_index=True,
                    )

                with st.expander("View generated SQL"):
                    st.code(generated_sql, language="sql")

                # Save the most recent successful query.
                st.session_state.eben_last_question = question.strip()
                st.session_state.eben_last_result = query_result.copy()
                st.session_state.eben_last_sql = generated_sql

                st.session_state.eben_history.append(
                    {
                        "question": question.strip(),
                        "summary": summary,
                    }
                )

        except Exception as error:
            st.error(
                "EBEN couldn't answer that question. "
                "Try rephrasing it."
            )
            st.exception(error)
