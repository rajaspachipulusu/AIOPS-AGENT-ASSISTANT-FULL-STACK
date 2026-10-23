"""
Unit tests for the SQL safety guardrails (app.text_to_sql). These are pure
and deterministic — no LLM or network calls — so they run fast and reliably
in CI.
"""
from requests.exceptions import Timeout
import pytest

from app.text_to_sql import validate_sql, UnsafeSQLError, SQLGenerationError, MAX_ROWS, _call_ollama


def test_allows_simple_select():
    result = validate_sql("SELECT * FROM employees")
    assert result.strip().upper().startswith("SELECT")
    assert "LIMIT" in result.upper()


def test_allows_with_cte():
    sql = "WITH x AS (SELECT * FROM employees) SELECT * FROM x"
    result = validate_sql(sql)
    assert "LIMIT" in result.upper()


def test_preserves_existing_limit():
    sql = "SELECT * FROM employees LIMIT 5"
    result = validate_sql(sql)
    assert result.strip().rstrip(";").upper().endswith("LIMIT 5")


def test_adds_default_limit_when_missing():
    sql = "SELECT * FROM employees"
    result = validate_sql(sql)
    assert f"LIMIT {MAX_ROWS}" in result


@pytest.mark.parametrize("sql", [
    "DELETE FROM employees",
    "UPDATE employees SET salary = 0",
    "DROP TABLE employees",
    "INSERT INTO employees (name) VALUES ('x')",
    "TRUNCATE employees",
    "ALTER TABLE employees ADD COLUMN x INT",
])
def test_blocks_destructive_statements(sql):
    with pytest.raises(UnsafeSQLError):
        validate_sql(sql)


def test_blocks_multiple_statements():
    with pytest.raises(UnsafeSQLError):
        validate_sql("SELECT * FROM employees; DROP TABLE employees;")


def test_blocks_dos_patterns():
    with pytest.raises(UnsafeSQLError):
        validate_sql("SELECT pg_sleep(100)")


def test_blocks_non_select_statement_type():
    with pytest.raises(UnsafeSQLError):
        validate_sql("EXPLAIN SELECT * FROM employees")


def test_call_ollama_retries_on_timeout_then_succeeds(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": "SELECT 1;"}

    calls = {"count": 0}

    def fake_post(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise Timeout("first timeout")
        return FakeResponse()

    monkeypatch.setattr("app.text_to_sql.requests.post", fake_post)
    out = _call_ollama("test prompt")
    assert out == "SELECT 1;"
    assert calls["count"] == 2


def test_call_ollama_raises_sql_generation_error_after_retries(monkeypatch):
    def fake_post(*args, **kwargs):
        raise Timeout("persistent timeout")

    monkeypatch.setattr("app.text_to_sql.requests.post", fake_post)

    with pytest.raises(SQLGenerationError, match="timed out"):
        _call_ollama("test prompt")
