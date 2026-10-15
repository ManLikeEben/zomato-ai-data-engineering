import duckdb
import pytest

from src.text_to_sql import execution_service


def test_retries_after_database_error(monkeypatch):
    """EBEN should retry after the first query fails."""

    attempts = []

    def fake_generate_sql(question, error_feedback=None):
        attempts.append(error_feedback)

        if len(attempts) == 1:
            return "SELECT * FROM nonexistent_table LIMIT 10"

        return "SELECT 1 AS result LIMIT 100"

    def fake_connect(*args, **kwargs):
        return duckdb.connect(":memory:")

    # Replace SQL generation and connection creation only.
    monkeypatch.setattr(
        execution_service,
        "generate_sql",
        fake_generate_sql,
    )

    monkeypatch.setattr(
        execution_service,
        "duckdb",
        type(
            "FakeDuckDB",
            (),
            {
                "connect": staticmethod(fake_connect),
                "Error": duckdb.Error,
            },
        ),
    )

    sql, result = execution_service.execute_query(
        "Give me a simple test result."
    )

    assert len(attempts) == 2
    assert attempts[0] is None
    assert attempts[1] is not None
    assert "Previous error" in attempts[1]
    assert "SELECT 1" in sql
    assert result.iloc[0]["result"] == 1


def test_stops_after_maximum_attempts(monkeypatch):
    """EBEN should stop after two failed attempts."""

    attempts = []

    def fake_generate_sql(question, error_feedback=None):
        attempts.append(error_feedback)
        return "SELECT * FROM nonexistent_table LIMIT 10"

    def fake_connect(*args, **kwargs):
        return duckdb.connect(":memory:")

    monkeypatch.setattr(
        execution_service,
        "generate_sql",
        fake_generate_sql,
    )

    monkeypatch.setattr(
        execution_service,
        "duckdb",
        type(
            "FakeDuckDB",
            (),
            {
                "connect": staticmethod(fake_connect),
                "Error": duckdb.Error,
            },
        ),
    )

    with pytest.raises(RuntimeError, match="after 2 attempts"):
        execution_service.execute_query(
            "Give me a test result."
        )

    assert len(attempts) == 2