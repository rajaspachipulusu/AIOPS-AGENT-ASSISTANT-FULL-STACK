"""
Agent layer: uses Ollama's native tool-calling to decide, for a given user
question, whether to query the structured database (Text-to-SQL) or search
the enterprise document corpus (RAG), then executes that tool and returns
a unified response.

This is a simple single-step "router" agent: one tool call per question.
It can be extended to multi-step tool use (e.g., calling both tools and
combining results) without changing the public `run_agent` interface.
"""
import json

import requests
from sqlalchemy.orm import Session

from app.config import get_settings
from app.text_to_sql import ask as sql_ask
from app.rag import answer_from_docs

CHAT_URL = f"{get_settings().ollama_base_url}/api/chat"
MODEL = "qwen3:8b"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_database",
            "description": (
                "Answer questions about employees, servers, incidents, and "
                "vulnerabilities by querying the structured operational "
                "database. Use this for questions involving counts, filters, "
                "lists, or specific records (e.g. salaries, open incidents, "
                "vulnerability counts, server details)."
            ),
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "Answer questions about company policies, standard operating "
                "procedures (SOPs), SLAs, or processes (e.g. incident "
                "response steps, change management process, vulnerability "
                "remediation policy) by searching enterprise documents."
            ),
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
            },
        },
    },
]


class AgentError(Exception):
    pass


def _decide_tool(question: str) -> dict:
    response = requests.post(
        CHAT_URL,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": question}],
            "stream": False,
            "tools": TOOLS,
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    tool_calls = data.get("message", {}).get("tool_calls") or []
    if not tool_calls:
        # Model answered directly without picking a tool; default to DB query
        # since that is the primary use case of this app.
        return {"name": "query_database", "arguments": {"question": question}}

    call = tool_calls[0]["function"]
    return {"name": call["name"], "arguments": call["arguments"]}


def run_agent(db: Session, question: str) -> dict:
    decision = _decide_tool(question)
    tool_name = decision["name"]
    tool_question = decision["arguments"].get("question", question)

    if tool_name == "search_documents":
        result = answer_from_docs(tool_question)
        return {
            "tool_used": "search_documents",
            "question": question,
            "answer": result["answer"],
            "sources": result["sources"],
        }

    if tool_name == "query_database":
        result = sql_ask(db, tool_question)
        return {
            "tool_used": "query_database",
            "question": question,
            "sql": result["sql"],
            "rows": result["rows"],
            "row_count": result["row_count"],
            "answer": result["explanation"],
        }

    raise AgentError(f"Unknown tool selected by agent: {tool_name}")
