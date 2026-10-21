from pathlib import Path

import duckdb
import pandas as pd
import requests

from src.text_to_sql.query_service import generate_sql

PROJECT_ROOT = Path(__file__).resolve().parents[2]

LOCAL_DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "cloud"
    / "zomato_cloud.duckdb"
)

HF_REPO_ID = "TheHelpedOne/zomato-cloud-analytics"
HF_DB_FILENAME = "zomato_cloud.duckdb"

MAX_ATTEMPTS = 2


def get_database_path() -> Path:
    """Return the local database or download it from Hugging Face."""

    if LOCAL_DATABASE_PATH.exists():
        return LOCAL_DATABASE_PATH

    from huggingface_hub import hf_hub_download

    return Path(
        hf_hub_download(
            repo_id=HF_REPO_ID,
            filename=HF_DB_FILENAME,
            repo_type="dataset",
        )
    )


def execute_query(question: str) -> tuple[str, pd.DataFrame]:
    """Generate, validate, and execute SQL with one recovery attempt."""

    if not question or not question.strip():
        raise ValueError("Please enter a question.")

    error_feedback = None
    last_error = None

    database_path = get_database_path()

    connection = duckdb.connect(
        str(database_path),
        read_only=True,
    )

    try:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                sql = generate_sql(
                    question,
                    error_feedback=error_feedback,
                )

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

            except requests.exceptions.RequestException as error:
                raise RuntimeError(
                    "EBEN could not reach the AI service. "
                    "Please try again shortly. If the problem "
                    "continues, check the AI provider and API quota."
                ) from error

    finally:
        connection.close()

    raise RuntimeError(
        f"EBEN could not answer the question after "
        f"{MAX_ATTEMPTS} attempts. Last error: {last_error}"
    ) from last_error