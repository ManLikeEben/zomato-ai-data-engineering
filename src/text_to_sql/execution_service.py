from pathlib import Path

import duckdb
import pandas as pd

from src.text_to_sql.query_service import generate_sql

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "warehouse" / "zomato.duckdb"
MAX_ATTEMPTS = 2


def execute_query(question: str) -> tuple[str, pd.DataFrame]:
    """Generate, validate, and execute SQL with one recovery attempt."""

    if not question or not question.strip():
        raise ValueError("Please enter a question.")

    error_feedback = None
    last_error = None

    connection = duckdb.connect(
        str(DATABASE_PATH),
        read_only=True,
    )

    try:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                # Generate SQL and validate it.
                sql = generate_sql(
                    question,
                    error_feedback=error_feedback,
                )

                # Execute the validated query.
                result = connection.execute(sql).fetchdf()

                return sql, result

            except (ValueError, duckdb.Error) as error:
                last_error = error

                if attempt == MAX_ATTEMPTS:
                    break

                error_feedback = (
                    f"Original question: {question}\n\n"
                    f"Previous error: {type(error).__name__}: {error}\n\n"
                    "Correct the SQL for DuckDB. Use only approved "
                    "tables and existing columns. Return one SELECT "
                    "query without Markdown or explanations."
                )

    finally:
        connection.close()

    raise RuntimeError(
        f"EBEN could not answer the question after "
        f"{MAX_ATTEMPTS} attempts. Last error: {last_error}"
    ) from last_error
