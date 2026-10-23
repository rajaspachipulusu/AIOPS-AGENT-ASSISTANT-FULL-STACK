"""
Text-to-SQL core logic:
 1. Build a description of the DB schema.
 2. Ask the LLM (via Ollama) to convert a natural language question into SQL.
 3. Validate the SQL is read-only (guardrail).
 4. Execute against Postgres using a restricted, read-only DB role.
 5. Ask the LLM to explain the result in plain English.
"""
import json
import re

import requests
import sqlparse
from requests import RequestException
from requests.exceptions import Timeout
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.config import get_settings

OLLAMA_URL = f"{get_settings().ollama_base_url}/api/generate"
MODEL = "qwen3:8b"
MAX_ROWS = 200
QUERY_TIMEOUT_SECONDS = 5
OLLAMA_TIMEOUT_SECONDS = 120
OLLAMA_MAX_RETRIES = 2

SCHEMA_DESCRIPTION = """
Tables:

employees(id, name, department, role, hire_date, salary, years_experience)
servers(id, hostname, environment, os, team)
incidents(id, title, severity, status, team, server_id, created_date, resolved_date, description)
  -- severity: P1, P2, P3, P4 (P1 = most critical)
  -- status: open, in_progress, resolved
vulnerabilities(id, cve_id, severity, status, server_id, discovered_date)
  -- severity: Critical, High, Medium, Low
  -- status: open, remediated

Relationships:
incidents.server_id -> servers.id
vulnerabilities.server_id -> servers.id
"""

# Statement-level keywords that must never appear, even inside a CTE/subquery.
FORBIDDEN_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|grant|revoke|create|"
    r"vacuum|copy|call|do|merge|refresh|reindex|comment|security|"
    r"pg_sleep|pg_terminate_backend|pg_cancel_backend)\b",
    re.IGNORECASE,
)

ALLOWED_STATEMENT_TYPES = {"SELECT", "UNKNOWN"}  # sqlparse classifies WITH as UNKNOWN


class SQLGenerationError(Exception):
    pass


class UnsafeSQLError(Exception):
    pass


def _call_ollama(prompt: str) -> str:
    last_error: Exception | None = None
    for attempt in range(1, OLLAMA_MAX_RETRIES + 1):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={"model": MODEL, "prompt": prompt, "stream": False},
                timeout=OLLAMA_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json()["response"]
        except Timeout as e:
            last_error = e
            if attempt == OLLAMA_MAX_RETRIES:
                raise SQLGenerationError(
                    "Ollama timed out while generating SQL/explanation. "
                    "Ensure Ollama is running and model 'qwen3:8b' is available, "
                    "then retry."
                ) from e
        except RequestException as e:
            raise SQLGenerationError(
                f"Failed to contact Ollama at {OLLAMA_URL}: {e}"
            ) from e

    raise SQLGenerationError("Failed to contact Ollama.") from last_error


def _extract_sql(raw: str) -> str:
    """Pull the SQL out of an LLM response that may include markdown fences or reasoning."""
    fenced = re.search(r"```sql\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1).strip()
    else:
        fenced_any = re.search(r"```\s*(.*?)```", raw, re.DOTALL)
        candidate = fenced_any.group(1).strip() if fenced_any else raw.strip()

    match = re.search(r"(select|with)\b.*", candidate, re.IGNORECASE | re.DOTALL)
    if not match:
        raise SQLGenerationError(f"Could not find SQL in LLM output: {raw[:300]}")
    sql = match.group(0).strip()
    sql = sql.rstrip(";") + ";"
    return sql


def generate_sql(question: str) -> str:
    prompt = f"""You are a PostgreSQL expert. Given the schema below, write a single
read-only SQL SELECT query that answers the user's question.

Schema:
{SCHEMA_DESCRIPTION}

Rules:
- Only output SQL, wrapped in a ```sql code block.
- Only use SELECT statements (no INSERT/UPDATE/DELETE/DDL).
- Use explicit JOINs when combining tables.
- Limit results to 100 rows unless the question implies otherwise.

Question: {question}
"""
    raw = _call_ollama(prompt)
    sql = _extract_sql(raw)
    return sql


def _ensure_row_limit(sql: str, max_rows: int = MAX_ROWS) -> str:
    """Force a hard LIMIT regardless of what the LLM produced, without
    trusting string-matching alone to decide whether one already exists."""
    parsed = sqlparse.parse(sql)[0]
    tokens = [t for t in parsed.tokens if not t.is_whitespace]
    has_limit = any(t.ttype is sqlparse.tokens.Keyword and t.value.upper() == "LIMIT" for t in tokens)
    sql_no_semicolon = sql.rstrip().rstrip(";")
    if has_limit:
        return sql_no_semicolon + ";"
    return f"{sql_no_semicolon} LIMIT {max_rows};"


def validate_sql(sql: str) -> str:
    """Validates the SQL is a single, safe, read-only statement.
    Returns a (possibly rewritten) SQL string with a row limit enforced.
    Raises UnsafeSQLError if the query cannot be considered safe.
    """
    statements = sqlparse.parse(sql)
    if len(statements) != 1:
        raise UnsafeSQLError("Only a single SQL statement is allowed.")

    stmt = statements[0]
    stmt_type = stmt.get_type()  # 'SELECT', 'UNKNOWN' (covers WITH), etc.
    if stmt_type not in ALLOWED_STATEMENT_TYPES:
        raise UnsafeSQLError(f"Only SELECT queries are allowed (got {stmt_type}).")

    stripped = sql.strip().lower()
    if not (stripped.startswith("select") or stripped.startswith("with")):
        raise UnsafeSQLError("Only SELECT queries are allowed.")

    if FORBIDDEN_KEYWORDS.search(sql):
        raise UnsafeSQLError("Query contains a forbidden keyword.")

    if ";" in sql.rstrip(";"):
        raise UnsafeSQLError("Multiple statements are not allowed.")

    return _ensure_row_limit(sql)


def execute_sql(db: Session, sql: str) -> list[dict]:
    try:
        db.execute(text(f"SET LOCAL statement_timeout = '{QUERY_TIMEOUT_SECONDS}s'"))
        result = db.execute(text(sql))
        columns = result.keys()
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return rows
    except OperationalError as e:
        raise UnsafeSQLError(f"Query failed or timed out: {e}")
    finally:
        db.rollback()  # always discard; connection is read-only anyway


def explain_result(question: str, sql: str, rows: list[dict]) -> str:
    preview = json.dumps(rows[:20], default=str)
    prompt = f"""The user asked: "{question}"

This SQL was run:
{sql}

It returned {len(rows)} row(s). Here is a preview (up to 20 rows) as JSON:
{preview}

Write a short, plain-English answer (2-4 sentences) summarizing the result for
a business user. Do not repeat the SQL. Do not use markdown.
"""
    return _call_ollama(prompt).strip()


def ask(db: Session, question: str) -> dict:
    # Backward compatibility for older snippets that used ask(question, db).
    if isinstance(db, str) and isinstance(question, Session):
        db, question = question, db

    if not isinstance(db, Session):
        raise TypeError("ask() expects arguments in order (db_session, question)")
    if not isinstance(question, str):
        raise TypeError("ask() expects 'question' to be a string")

    sql = generate_sql(question)
    safe_sql = validate_sql(sql)
    rows = execute_sql(db, safe_sql)
    explanation = explain_result(question, safe_sql, rows)
    return {
        "question": question,
        "sql": safe_sql,
        "rows": rows,
        "row_count": len(rows),
        "explanation": explanation,
    }
