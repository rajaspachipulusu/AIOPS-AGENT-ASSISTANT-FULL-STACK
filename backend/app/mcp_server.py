"""
MCP server exposing this app's core capabilities as tools usable by any
MCP-compatible client (e.g. Claude Desktop, other agents):

  - query_database: Text-to-SQL over the operational database.
  - search_documents: RAG search over enterprise policy/SOP documents.

Run standalone with:  python -m app.mcp_server
(Uses stdio transport, the standard for local MCP clients.)
"""
from mcp.server.mcpserver import MCPServer

from app.db import ReadOnlySessionLocal
from app.text_to_sql import ask as sql_ask
from app.rag import answer_from_docs

mcp = MCPServer("aiops-assistant")


@mcp.tool()
def query_database(question: str) -> dict:
    """Answer questions about employees, servers, incidents, and
    vulnerabilities by converting the question to SQL and querying the
    operational PostgreSQL database (read-only).

    Args:
        question: A natural language question about employees, servers,
            incidents, or vulnerabilities.
    """
    db = ReadOnlySessionLocal()
    try:
        result = sql_ask(db, question)
        return {
            "sql": result["sql"],
            "rows": result["rows"],
            "row_count": result["row_count"],
            "explanation": result["explanation"],
        }
    finally:
        db.close()


@mcp.tool()
def search_documents(question: str) -> dict:
    """Answer questions about company policies, SOPs, SLAs, or processes
    (incident response, change management, vulnerability remediation) by
    searching the enterprise document corpus.

    Args:
        question: A natural language question about policies or procedures.
    """
    result = answer_from_docs(question)
    return {"answer": result["answer"], "sources": result["sources"]}


if __name__ == "__main__":
    mcp.run(transport="stdio")
