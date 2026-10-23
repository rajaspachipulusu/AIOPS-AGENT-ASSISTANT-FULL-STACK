# AI Ops Assistant - AI Agent Customization Guide

This document helps AI coding agents (Copilot, Claude, etc.) understand the architecture, execution flow, and key patterns in this fullstack AI application.

## Project Structure

```
fullstack-ai-assistant/
├── backend/          FastAPI application (Python)
│   ├── app/          Core application modules
│   │   ├── main.py              API routes and FastAPI app initialization
│   │   ├── agent.py             Tool routing logic (SQL vs RAG decision)
│   │   ├── text_to_sql.py       LLM→SQL generation + validation + execution
│   │   ├── rag.py               RAG: document ingestion, chunking, retrieval
│   │   ├── auth.py              JWT authentication (demo: admin/changeme123)
│   │   ├── db.py                SQLAlchemy engines (app + read-only)
│   │   ├── models.py            ORM definitions (Employee, Server, Incident, Vulnerability)
│   │   ├── seed.py              Sample data generator (run once after DB setup)
│   │   ├── config.py            Settings from .env
│   │   ├── mcp_server.py        MCP protocol server
│   │   └── logging_config.py    JSON structured logging
│   ├── docs_corpus/             Markdown documents for RAG (policies, SOPs)
│   ├── chroma_store/            ChromaDB vector store (persisted embeddings)
│   ├── db_init/                 Database initialization scripts
│   ├── tests/                   Test files (test_api.py, test_auth.py, test_text_to_sql_guardrails.py)
│   ├── requirements.txt         Python dependencies
│   └── .env                     Environment variables (database URLs, JWT secret, demo credentials)
├── frontend/         Next.js application (TypeScript)
│   ├── src/app/
│   │   ├── page.tsx             Main chat UI component
│   │   ├── layout.tsx           App layout wrapper
│   │   ├── LoginForm.tsx        Authentication UI
│   │   ├── ResultCard.tsx       Result display component
│   │   ├── types.ts             TypeScript interfaces (ChatEntry, etc.)
│   │   └── globals.css          Tailwind styles
│   ├── package.json             Node.js dependencies
│   ├── next.config.ts           Next.js configuration
│   ├── tsconfig.json            TypeScript configuration
│   └── AGENTS.md                Frontend-specific agent instructions
├── docs/                        Project documentation
├── REVERSE_ENGINEERING.md       Comprehensive architectural deep-dive
└── docker-compose.yml           Container orchestration (Postgres, backend, frontend)
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | Next.js 14+, TypeScript, Tailwind CSS 4 | Chat UI, request handling, token storage |
| **Backend** | FastAPI 0.142+, SQLAlchemy 2.1, Pydantic | REST API, ORM, validation |
| **Database** | PostgreSQL 16 | Persistent data (employees, servers, incidents, vulnerabilities) |
| **LLM** | Ollama (local) + qwen3:8b | Text generation, SQL generation, agent decision-making |
| **Embeddings** | Ollama + nomic-embed-text | Document embedding for RAG |
| **Vector DB** | ChromaDB 1.5+ | Persisted embeddings and chunk storage |
| **MCP** | mcp 2.2+ | Tool exposure protocol for external clients |
| **Auth** | PyJWT, bcrypt | Token-based authentication (demo single-user) |
| **Testing** | pytest 9.1+ | API and SQL guardrail tests |

## Prerequisites & Setup

### System Requirements
- **Python**: 3.14 (via `/opt/homebrew/bin/python3.14`)
- **Node.js**: Latest LTS (via `/opt/homebrew/bin/node`)
- **PostgreSQL**: 18 (running as `brew service`, default port 5432)
- **Ollama**: Running locally on port 11434 with models downloaded:
  - `qwen3:8b` (LLM for generation, SQL, agent decisions)
  - `nomic-embed-text` (embeddings for RAG)

### Environment Variables (.env)
```
DATABASE_URL=postgresql+psycopg2://rajas.pr@localhost:5432/aiops
READONLY_DATABASE_URL=postgresql+psycopg2://aiops_reader:readonly_dev_pw@localhost:5432/aiops
APP_ENV=development
JWT_SECRET=dev-only-insecure-secret-change-me
DEMO_USERNAME=admin
DEMO_PASSWORD=changeme123
OLLAMA_BASE_URL=http://localhost:11434
```

## Complete Execution Flow

### Step 1: Verify Prerequisites
```bash
# Check Python
/opt/homebrew/bin/python3.14 --version

# Check Node.js
/opt/homebrew/bin/node --version

# Check PostgreSQL (must be running)
brew services list | grep postgres
psql -U postgres -c "SELECT version();"

# Check Ollama is running
curl http://localhost:11434/api/tags  # Should list qwen3:8b and nomic-embed-text
```

**Learning Point**: All services must be running **before** starting the backend. Ollama especially takes time to start; verify it's responsive.

---

### Step 2: Initialize Database & Backend

**Location**: `backend/`

#### 2a. Activate Virtual Environment
```bash
cd backend
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Learning Point**: The `.venv/bin/activate` script sets Python PATH and activates the isolated environment. All subsequent Python commands must run from here.

#### 2b. Create Tables & Roles (First-Time Only)
```bash
# Run database initialization script
psql -U postgres -d aiops -f /Users/rajas.pr/fullstack-ai-assistant/db_init/01_create_reader_role.sql
```

**What Happens**:
- Creates `aiops_reader` role (read-only, used only for LLM-generated SQL execution)
- Sets statement timeout to 5 seconds (guardrail: prevents long-running queries)
- Grants SELECT-only privileges to public schema

**Learning Point**: The separate read-only role ensures that even if the SQL validation code has a bug, the LLM cannot modify/delete data. This is a **defense-in-depth** security pattern.

#### 2c. Seed Sample Data
```bash
cd backend
source .venv/bin/activate
python -m app.seed
```

**What Happens**:
- Drops existing tables (fresh start)
- Creates schema from SQLAlchemy models: employees, servers, incidents, vulnerabilities
- Generates ~200 sample records across tables
- Establishes foreign key relationships

**Database Structure After Seeding**:
- **employees** (40 records): name, department, role, hire_date, salary, years_experience
- **servers** (25 records): hostname, environment (prod/staging/dev), os, team
- **incidents** (60 records): title, severity (P1-P4), status, team, server_id, created_date, resolved_date
- **vulnerabilities** (80 records): cve_id, severity (Critical/High/Medium/Low), status (open/remediated), server_id, discovered_date

**Learning Point**: The demo data is realistic (salaries, incident dates spanning 2021-2025, multiple environments). This allows testing realistic Text-to-SQL queries like "employees earning >15 lakh with 5+ years experience".

#### 2d. Ingest RAG Documents
```bash
cd backend
source .venv/bin/activate
python -c "from app.rag import ingest_docs; print(f'Ingested {ingest_docs()} chunks')"
```

**What Happens**:
- Reads all markdown files from `backend/docs_corpus/`
- Chunks documents (800 chars per chunk, 100 char overlap)
- Embeds each chunk using Ollama `nomic-embed-text`
- Stores embeddings + metadata in ChromaDB (persisted to `backend/chroma_store/`)

**Documents Included** (sample enterprise content):
- `change_management_policy.md` - change control procedures
- `incident_management_sop.md` - P1/P2/P3/P4 incident response workflows
- `vulnerability_management_policy.md` - remediation SLAs, severity definitions

**Learning Point**: This RAG layer answers **procedural questions** ("What's the incident response process?") vs. **data questions** ("How many open incidents?"). The LLM's agent decides which tool to use.

---

### Step 3: Start Backend API

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --port 8000 --reload
```

**Output Indicates Success**:
```
Uvicorn running on http://127.0.0.1:8000
```

**Available Endpoints**:
- `GET /health` - always OK
- `GET /health/db` - checks database connectivity
- `POST /api/login` - authentication (username/password → JWT token)
- `POST /api/ask` - direct Text-to-SQL query
- `POST /api/ask-docs` - direct RAG document search
- `POST /api/agent` - hybrid (router decides SQL vs RAG)
- `GET /docs` - Swagger UI with all endpoints documented

**API Docs**: Open http://localhost:8000/docs in browser to test endpoints interactively.

**Learning Point**: The `--reload` flag watches for file changes and restarts the server automatically. This is critical for development iteration.

---

### Step 4: Start Frontend

**Location**: `frontend/`

#### 4a. Install Dependencies
```bash
cd frontend
npm install
```

**Learning Point**: Next.js 16.3.8 has significant internal changes; the installed version matters for compatibility. See `frontend/node_modules/next/dist/docs/` for version-specific features.

#### 4b. Start Dev Server
```bash
npm run dev
```

**Output Indicates Success**:
```
▲ Next.js 16.3.8
- Local: http://localhost:3000
- Environments: .env.local
```

**UI Available At**: http://localhost:3000

**Learning Point**: The Next.js dev server uses hot module reloading (HMR). Changes to TypeScript/JSX files automatically refresh the browser.

---

### Step 5: Use the Application

#### 5a. Login
1. Navigate to http://localhost:3000
2. Enter credentials: **admin** / **changeme123**
3. Click "Login"

**What Happens**:
- Frontend POSTs to `/api/login` with username/password
- Backend validates against demo credentials (hardcoded in `.env`)
- Backend returns JWT token
- Frontend stores token in localStorage
- Subsequent API calls include `Authorization: Bearer {token}` header

**Learning Point**: This is a **demo single-user auth system**. In production, use OAuth, SAML, or a real auth provider. The token is **never refreshed**; it expires when localStorage is cleared.

#### 5b. Ask a Question
Example questions trigger different backends:

**Text-to-SQL Questions** (query the database):
- "How many critical vulnerabilities are currently open?"
- "Show employees earning more than 15 lakh with 5+ years experience"
- "Which team has the most open incidents?"

**RAG Questions** (search enterprise documents):
- "What is the procedure for a P1 incident?"
- "What are the SLA timelines for remediating vulnerabilities?"
- "Explain the change management process"

**Agent Decides** (you don't need to choose):
- The backend `/api/agent` endpoint automatically routes based on question content

#### 5c. View Results
**Response Structure**:
```json
{
  "question": "...",
  "tool_used": "query_database" or "search_documents",
  "answer": "...",
  "sql": "SELECT ... FROM ...",  // if query_database
  "rows": [{...}],                // if query_database
  "sources": [...]                // if search_documents
}
```

---

## Core Processing Flows

### Flow 1: Text-to-SQL (Database Query)

```
User Question
    ↓
[backend/app/text_to_sql.py] ask()
    ↓
1. Build SCHEMA_DESCRIPTION (tables, columns, relationships)
2. Prompt LLM: "Given this schema, convert to SQL: {question}"
3. LLM calls Ollama qwen3:8b → returns SQL (possibly with markdown fences)
    ↓
4. Extract SQL from response (strip fences, find SELECT/WITH clause)
    ↓
5. Validate SQL (guardrails):
   - Parse with sqlparse, check statement type is SELECT
   - Scan for forbidden keywords (INSERT, UPDATE, DELETE, DROP, etc.)
   - (read-only role also prevents writes as secondary guardrail)
    ↓
6. Execute against readonly_engine (aiops_reader role):
   - Max 200 rows returned
   - 5-second timeout
    ↓
7. Prompt LLM again: "Explain this query result in plain English"
    ↓
8. Return JSON: {question, sql, rows, explanation}
```

**Guardrails Implemented**:
1. **Role-based** (PostgreSQL): read-only `aiops_reader` role cannot execute INSERT/UPDATE/DELETE
2. **Statement timeout**: 5-second limit prevents long-running queries
3. **Keyword validation**: forbidden keywords checked regex before execution
4. **Row limit**: max 200 rows returned (prevents data exfiltration)

**Learning Point**: Multiple layers of defense ensure LLM-generated SQL cannot harm the database, even if one layer is bypassed.

---

### Flow 2: RAG (Document Search)

```
User Question
    ↓
[backend/app/rag.py] answer_from_docs()
    ↓
1. Embed question using Ollama nomic-embed-text → vector
    ↓
2. Query ChromaDB collection for top-4 similar chunks
   (similarity based on cosine distance in embedding space)
    ↓
3. Build context: {top_4_chunks_concatenated}
    ↓
4. Prompt LLM: "Using only this context, answer: {question}"
    ↓
5. LLM calls Ollama → returns answer grounded in documents
    ↓
6. Return JSON: {question, answer, sources: [{filename, chunk_index}]}
```

**Document Ingestion (on demand)**:
```python
# Run this after editing docs_corpus/*.md
ingest_docs()

# Process:
# 1. Read all *.md files from docs_corpus/
# 2. Chunk with 800-char size, 100-char overlap
# 3. Embed each chunk (calls Ollama nomic-embed-text)
# 4. Store in ChromaDB with metadata (source filename, chunk index)
```

**Learning Point**: The RAG retrieval is **semantic** (based on embedding similarity), not keyword-based. This allows matching "incident response workflow" to documents containing "P1 procedures" even without exact keyword match.

---

### Flow 3: Agent Routing (Hybrid)

```
User Question
    ↓
[backend/app/agent.py] run_agent()
    ↓
1. Define two tools for Ollama's native tool-calling:
   - query_database (for structured data questions)
   - search_documents (for procedural/policy questions)
    ↓
2. Prompt LLM with tools: "You have these two tools. Which should you use?"
    ↓
3. LLM's Ollama generates tool_calls response:
   {
     "tool_calls": [
       {
         "function": {
           "name": "query_database" or "search_documents",
           "arguments": {"question": "..."}
         }
       }
     ]
   }
    ↓
4. Extract tool name and arguments
    ↓
5. Execute chosen tool:
   - If query_database: call text_to_sql.ask()
   - If search_documents: call rag.answer_from_docs()
    ↓
6. Return unified response: {question, tool_used, answer, ...tool-specific fields}
```

**Learning Point**: Ollama's native tool-calling is simpler than managing function routing manually. The LLM sees tool definitions and decides which to invoke. This pattern is extensible: add more tools by extending the TOOLS list in agent.py.

---

## Key Files & Their Purposes

| File | Purpose | Key Functions |
|------|---------|---|
| [backend/app/main.py](backend/app/main.py) | FastAPI app + route definitions | `@app.post("/api/login")`, `@app.post("/api/agent")`, etc. |
| [backend/app/text_to_sql.py](backend/app/text_to_sql.py) | LLM→SQL pipeline | `ask()`, `validate_sql()`, `execute_sql()`, `explain_result()` |
| [backend/app/rag.py](backend/app/rag.py) | Document ingestion & retrieval | `ingest_docs()`, `answer_from_docs()`, `_chunk_text()`, `_embed()` |
| [backend/app/agent.py](backend/app/agent.py) | Tool routing logic | `run_agent()`, `_decide_tool()` |
| [backend/app/models.py](backend/app/models.py) | SQLAlchemy ORM | `Employee`, `Server`, `Incident`, `Vulnerability` |
| [backend/app/seed.py](backend/app/seed.py) | Sample data generator | `seed()` - call as `python -m app.seed` |
| [backend/app/db.py](backend/app/db.py) | Database connection setup | `engine`, `readonly_engine`, `SessionLocal`, `get_db()` |
| [backend/app/auth.py](backend/app/auth.py) | JWT token handling | `authenticate()`, `create_access_token()`, `get_current_user()` |
| [backend/app/config.py](backend/app/config.py) | Settings from .env | `Settings` class, `get_settings()` |
| [frontend/src/app/page.tsx](frontend/src/app/page.tsx) | Main chat UI | `Home` component, chat state, token management |
| [frontend/src/app/LoginForm.tsx](frontend/src/app/LoginForm.tsx) | Authentication UI | Login form submission |
| [frontend/src/app/ResultCard.tsx](frontend/src/app/ResultCard.tsx) | Result display | Formats and renders SQL/RAG responses |

---

## Testing

### Run Backend Tests
```bash
cd backend
source .venv/bin/activate
pytest
```

**Tests Included**:
- `test_api.py` - endpoint integration tests (login, /health, /api/agent)
- `test_auth.py` - token generation and validation
- `test_text_to_sql_guardrails.py` - SQL validation (ensures forbidden keywords are caught)

**Learning Point**: Tests verify that the guardrails actually prevent dangerous queries. Always run these before modifying validation logic.

---

## Common Development Tasks

### Add a New Document to RAG
1. Add markdown file to `backend/docs_corpus/` (e.g., `my_policy.md`)
2. Run ingestion:
   ```bash
   cd backend
   source .venv/bin/activate
   python -c "from app.rag import ingest_docs; print(f'Ingested {ingest_docs()} chunks')"
   ```
3. Next query will retrieve from the new document

### Modify Text-to-SQL Guardrails
1. Edit `backend/app/text_to_sql.py`:
   - Add keywords to `FORBIDDEN_KEYWORDS` regex
   - Add validation to `validate_sql()` function
   - Add statement type to `ALLOWED_STATEMENT_TYPES`
2. Run tests to verify:
   ```bash
   cd backend
   source .venv/bin/activate
   pytest tests/test_text_to_sql_guardrails.py -v
   ```

### Add a New API Endpoint
1. Edit `backend/app/main.py`
2. Define request/response models using Pydantic
3. Add route with authentication: `@app.post("/api/new-endpoint", dependencies=[Depends(get_current_user)])`
4. Test with curl or Swagger UI at `http://localhost:8000/docs`

### Change Demo Credentials
1. Edit `backend/.env`: `DEMO_USERNAME`, `DEMO_PASSWORD`
2. Restart backend: `uvicorn app.main:app --port 8000 --reload`
3. Login form will now accept new credentials

---

## MCP Server (Advanced)

The application also exposes tools via the Model Context Protocol, allowing external MCP-compatible clients (e.g., Claude Desktop) to query the database and documents.

```bash
cd backend
source .venv/bin/activate
python -m app.mcp_server
```

This starts an MCP server on stdio transport. Configure it in Claude Desktop's `claude_desktop_config.json` to grant Claude direct access to your operational data.

---

## Environment-Specific Notes

### Local Development (Current Setup)
- **Database**: Postgres on `localhost:5432` (default port)
- **Ollama**: Running on host machine `http://localhost:11434`
- **Frontend**: `http://localhost:3000`
- **Backend**: `http://localhost:8000`
- **Auth**: Demo single-user (admin/changeme123)

### Docker/Podman Deployment (See docker-compose.yml)
- **Database**: Postgres on `postgres:5432` (internal network) + port `5433` exposed on host
- **Ollama**: Reached via `http://host.containers.internal:11434` from containers
- **Backend**: Port `8000` exposed
- **Frontend**: Port `3000` exposed (served by container)
- **Network**: Services communicate via `aiops-net` bridge network

**Note**: The container setup requires Ollama to be running on the **host machine**, not inside a container (licensing/performance reasons). The backend container reaches it via Docker/Podman's `host.containers.internal` DNS alias.

---

## Troubleshooting

### "Cannot connect to Ollama"
- Verify `http://localhost:11434/api/tags` returns model list
- Check `OLLAMA_BASE_URL` in `.env` matches running Ollama
- In containers, use `http://host.containers.internal:11434` (Docker/Podman sets this up automatically)

### "Database role aiops_reader not found"
- Run `psql -U postgres -d aiops -f db_init/01_create_reader_role.sql` to create the role

### "ChromaDB throws error on import"
- Delete `backend/chroma_store/` and run `python -m app.seed` to re-initialize

### "Text-to-SQL returns 'Forbidden keyword found'"
- Check that query doesn't contain: INSERT, UPDATE, DELETE, DROP, ALTER, etc.
- This is intentional — it prevents LLM from modifying data

### "Frontend can't reach backend on localhost:8000"
- Verify backend is running: `curl http://localhost:8000/health`
- Check CORS: backend allows `http://localhost:3000` by default
- In `main.py`, `allow_origins` may need adjustment if frontend is on different host

---

## Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| **Separate read-only DB role** | Defense-in-depth: prevents data modification even if SQL validation fails |
| **Local Ollama, no API calls** | Cost (no usage), privacy (data stays on machine), latency (local), control (own models) |
| **ChromaDB vector store** | Lightweight, persistent, open-source; simpler than managed vector DBs |
| **Single-step agent routing** | Simpler than multi-step; extensible by adding tools to TOOLS list |
| **Pydantic models for validation** | FastAPI automatic request validation + type safety |
| **JWT tokens in localStorage** | Stateless; suitable for demo; production should use httpOnly cookies + refresh tokens |
| **SQLAlchemy ORM** | Type-safe, vendor-agnostic, relationship management |

---

## Resources & Next Steps

- **Architecture Deep-Dive**: See [REVERSE_ENGINEERING.md](REVERSE_ENGINEERING.md)
- **API Documentation**: Open [http://localhost:8000/docs](http://localhost:8000/docs) when backend is running
- **Frontend Setup**: See [frontend/README.md](frontend/README.md)
- **Backend Setup**: See [backend/requirements.txt](backend/requirements.txt) for dependencies
- **Database Schema**: Defined in [backend/app/models.py](backend/app/models.py)
- **Tests**: [backend/tests/](backend/tests/)

---

## Quick Reference: Startup Checklist

```
☐ Verify prerequisites (Python 3.14, Node.js, Postgres running, Ollama running)
☐ cd backend && source .venv/bin/activate
☐ pip install -r requirements.txt (first time only)
☐ psql -U postgres -d aiops -f db_init/01_create_reader_role.sql (first time only)
☐ python -m app.seed (generates demo data)
☐ python -c "from app.rag import ingest_docs; print(ingest_docs())" (ingests RAG docs)
☐ uvicorn app.main:app --port 8000 --reload (start backend)
☐ cd ../frontend && npm install (first time only)
☐ npm run dev (start frontend)
☐ Open http://localhost:3000, login with admin/changeme123
☐ Ask a question to verify the full pipeline works
```
