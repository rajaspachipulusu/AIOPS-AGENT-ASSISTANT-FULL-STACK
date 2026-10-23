# AIOps Agent Assistant

Agentic AI assistant for IT operations, built with Next.js + FastAPI + PostgreSQL + Ollama.

It combines:
- Text-to-SQL for structured operational data queries
- RAG for SOP/policy questions
- Tool-routing agent behavior to choose the right retrieval path

## Suggested Public Repo Name

aiops-agent-assistant

## Tech Stack

- Frontend: Next.js 16, React 19, Tailwind 4
- Backend: FastAPI, SQLAlchemy, Pydantic
- Data: PostgreSQL
- LLM: Ollama qwen3:8b
- Embeddings: Ollama nomic-embed-text
- Vector store: ChromaDB
- Tests: pytest

## Features

- Natural-language analytics over employees, incidents, servers, and vulnerabilities
- Read-only SQL execution path with guardrails and row limits
- Document-grounded answers using semantic retrieval over markdown corpus
- Single agent endpoint that routes between database and document tools
- MCP server for external tool-based clients

## Architecture

```text
User -> Next.js Chat UI -> FastAPI
                      -> /api/agent router
                         -> query_database -> text_to_sql -> PostgreSQL (read-only role)
                         -> search_documents -> rag -> ChromaDB + docs_corpus
```

## Quick Start

### 1) Prerequisites

- Python 3.14+
- Node.js 20.9+ (22+ recommended)
- PostgreSQL running locally
- Ollama running with models:
  - qwen3:8b
  - nomic-embed-text

If your shell does not include Homebrew binaries:

```bash
export PATH="/opt/homebrew/bin:$PATH"
```

### 2) Backend

```bash
cd backend
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env

# one-time role setup
psql -U postgres -d aiops -f ../db_init/01_create_reader_role.sql

# seed and ingest
python -m app.seed
python -c "from app.rag import ingest_docs; print(f'Ingested {ingest_docs()} chunks')"

uvicorn app.main:app --port 8000 --reload
```

### 3) Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 and sign in with demo credentials.

## API Endpoints

- GET /health
- GET /health/db
- POST /api/login
- POST /api/ask
- POST /api/ask-docs
- POST /api/agent

## Security Notes

- Do not commit real secrets or production credentials.
- Keep demo auth only for local/portfolio use.
- Rotate any secret if it has ever been committed.
- Use the dedicated read-only role for all LLM-generated SQL execution.

## Public Release Checklist

- Add screenshots and short demo GIF under docs/assets
- Add CI badge once GitHub Actions is configured
- Add CONTRIBUTING.md and CODE_OF_CONDUCT.md
- Add issue templates and pull request template
- Add architecture diagram image

## License

MIT. See LICENSE.
