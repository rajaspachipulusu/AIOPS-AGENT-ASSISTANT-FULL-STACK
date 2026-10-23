# Fullstack AI Assistant - Comprehensive Reverse Engineering Guide

**Document Purpose**: This guide provides a complete end-to-end explanation of the AI Ops Assistant project architecture, implementation details, security measures, and integration patterns. Use this to understand how the system works and answer technical interview questions.

**Last Updated**: October 2026
**Project Status**: Portfolio project with Text-to-SQL, RAG, Agent routing, and MCP server capabilities

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Technology Stack](#technology-stack)
3. [System Components](#system-components)
4. [Core Implementations](#core-implementations)
5. [Security & Guardrails](#security--guardrails)
6. [Database Design](#database-design)
7. [Integration Points](#integration-points)
8. [Use Cases & Testing](#use-cases--testing)
9. [Important Design Decisions](#important-design-decisions)
10. [Deployment Architecture](#deployment-architecture)

---

## Architecture Overview

### High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                          │
│                    port 3000                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ - Login/Auth (JWT tokens)                                │  │
│  │ - Chat interface                                         │  │
│  │ - Query submission & result display                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────────┘
                         │ HTTP/JSON
                         │
┌────────────────────────▼─────────────────────────────────────────┐
│                   Backend API (FastAPI)                          │
│                    port 8000                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Routes:                                                    │ │
│  │ - POST /api/login          → authentication              │ │
│  │ - POST /api/ask            → Text-to-SQL pipeline        │ │
│  │ - POST /api/ask-docs       → RAG search                  │ │
│  │ - POST /api/agent          → Agent routing (hybrid)      │ │
│  │ - GET /health              → health check                │ │
│  │ - GET /health/db           → DB connectivity check       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Core Modules (app/):                                           │
│  ├─ main.py           API route definitions                     │
│  ├─ agent.py          Tool routing & decision logic            │
│  ├─ text_to_sql.py    LLM→SQL generation + guardrails         │
│  ├─ rag.py            Document ingestion & retrieval           │
│  ├─ auth.py           JWT + demo user auth                     │
│  ├─ db.py             SQLAlchemy connection setup              │
│  ├─ models.py         ORM definitions                          │
│  ├─ mcp_server.py     MCP protocol server                      │
│  └─ logging_config.py JSON structured logging                 │
└────────┬─────────────────────────────────────────────────────┬──┘
         │                                                      │
         │ SQL queries (read-only)                             │
         │                                                      │
┌────────▼──────────────┐                                ┌─────▼──────────────┐
│  PostgreSQL 16        │                                │  Ollama (local)    │
│  port 5433 (docker)   │                                │  port 11434        │
│  port 5432 (local)    │                                │                    │
│                       │                                │  Models:           │
│  ├─ aiops DB          │                                │  - qwen3:8b (LLM)  │
│  │  ├─ employees      │                                │  - nomic-embed-text│
│  │  ├─ servers        │                                │  (embeddings)      │
│  │  ├─ incidents      │                                │                    │
│  │  └─ vulnerabilities│                                │  Chrome API        │
│  │                   │                                │  for chat/generate │
│  └─ reader role       │                                │  for embeddings    │
│    (read-only)        │                                └────────────────────┘
└───────────────────────┘
         │
         ▼
    ChromaDB (vector store)
    chroma_store/
    Local persistent embeddings
```

### Data Flow Patterns

**Pattern 1: Text-to-SQL Query**
```
User Question 
  → FastAPI /api/ask endpoint 
  → text_to_sql.py: generate_sql() calls Ollama 
  → LLM generates SQL 
  → validate_sql() applies guardrails 
  → execute_sql() runs against readonly_engine 
  → explain_result() generates natural English summary 
  → JSON response with SQL + rows + explanation
```

**Pattern 2: RAG Document Search**
```
User Question 
  → FastAPI /api/ask-docs endpoint 
  → rag.py: answer_from_docs() 
  → Embed question using Ollama nomic-embed-text 
  → ChromaDB retrieves top-4 similar chunks 
  → Build context from chunks 
  → LLM generates answer using only that context 
  → Return answer + sources
```

**Pattern 3: Agent Routing (Hybrid)**
```
User Question 
  → FastAPI /api/agent endpoint 
  → agent.py: run_agent() 
  → LLM decides: use Text-to-SQL or RAG? 
  → Execute chosen tool 
  → Return unified response (question, tool_used, answer, SQL/sources)
```

---

## Technology Stack

### Backend
- **Framework**: FastAPI 0.104+ (async HTTP, OpenAPI auto-docs)
- **ORM**: SQLAlchemy 2.0 (declarative models, session management)
- **Database Driver**: psycopg2 (PostgreSQL client)
- **LLM Integration**: Ollama (local models via HTTP API)
- **Vector DB**: ChromaDB (local persistent embeddings)
- **Auth**: PyJWT (token signing) + bcrypt (password hashing)
- **SQL Parsing**: sqlparse (statement validation)
- **MCP Protocol**: mcp-server-library (tool exposure)
- **Logging**: Python stdlib logging + JSON formatter
- **Request HTTP**: requests library

### Frontend
- **Framework**: Next.js 14+ (React, SSR/SSG)
- **Language**: TypeScript
- **Styling**: Tailwind CSS 3.4+
- **HTTP Client**: fetch API (native)
- **State**: React hooks (useState, useEffect)
- **Token Storage**: localStorage (session-only)

### Database
- **Primary**: PostgreSQL 16 (alpine docker image)
- **Schema**: 4 core tables (employees, servers, incidents, vulnerabilities)
- **Access Control**: Database roles (app user + restricted reader)
- **Persistence**: Docker volume (postgres_data)

### Deployment
- **Containerization**: Docker & Docker Compose
- **Network**: Bridge network (aiops-net) for inter-container communication
- **Local Dependencies**: Ollama server (host-only, not containerized)

**File Location**: [docker-compose.yml](docker-compose.yml)

---

## System Components

### 1. Frontend Application

**Location**: [frontend/](frontend/)

#### Key Files
- [src/app/page.tsx](frontend/src/app/page.tsx) - Main chat interface
- [src/app/LoginForm.tsx](frontend/src/app/LoginForm.tsx) - Authentication
- [src/app/ResultCard.tsx](frontend/src/app/ResultCard.tsx) - Result rendering
- [src/app/types.ts](frontend/src/app/types.ts) - TypeScript types
- [package.json](frontend/package.json) - Dependencies

#### Features Implemented
1. **Login Interface** (lines 1-50 in LoginForm.tsx)
   - JWT token storage in localStorage
   - Demo credentials: admin/changeme123
   - Token validation on app load

2. **Chat Interface** (lines 1-100 in page.tsx)
   - Message history display
   - Question input & submission
   - Auto-suggestion of sample questions
   - Loading states & error handling

3. **Result Rendering** (ResultCard.tsx)
   - Shows SQL queries + execution results for database queries
   - Shows citations & context relevance for document searches
   - Displays tool_used indicator (query_database vs search_documents)

#### API Integration Points
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// POST /api/agent (primary endpoint)
fetch(`${API_URL}/api/agent`, {
  headers: { Authorization: `Bearer ${token}` },
  body: JSON.stringify({ question })
})
```

### 2. Backend API (FastAPI)

**Location**: [backend/app/](backend/app/)

#### 2.1 Main API Routes

**File**: [main.py](backend/app/main.py) (lines 1-120)

**Core Endpoints**:

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|----------------|
| /health | GET | Server health check | No |
| /health/db | GET | Database connectivity | No |
| /api/login | POST | User authentication, returns JWT | No |
| /api/ask | POST | Text-to-SQL query | Yes |
| /api/ask-docs | POST | RAG document search | Yes |
| /api/agent | POST | Intelligent routing (SQL or RAG) | Yes |

**Example Response (Agent Route)**:
```json
{
  "tool_used": "query_database",
  "question": "How many critical vulnerabilities?",
  "answer": "There are currently 12 critical vulnerabilities...",
  "sql": "SELECT COUNT(*) FROM vulnerabilities WHERE severity='Critical' AND status='open'",
  "rows": [{"count": 12}],
  "row_count": 1
}
```

#### 2.2 Authentication Module

**File**: [auth.py](backend/app/auth.py)

**Implementation Details**:
- Demo single-user setup (username: `admin`, password: `changeme123`)
- Password stored as bcrypt hash (never in plaintext)
- JWT token creation with 60-minute expiry
- Bearer token validation in get_current_user() dependency

**Key Functions**:
- `authenticate(username, password)` → bool
- `create_access_token(username)` → JWT string
- `get_current_user(credentials)` → username (dependency for protected routes)

**Lines of Interest**:
- Token expiry: 60 minutes (line 13)
- Password hashing: bcrypt.gensalt() (line 22)
- JWT algorithm: HS256 (line 9)

### 3. Text-to-SQL Engine

**File**: [text_to_sql.py](backend/app/text_to_sql.py) (lines 1-250)

**Purpose**: Convert natural language questions to safe SQL queries, execute them, and explain results.

#### Workflow
```
Question → generate_sql() → Ollama LLM → _extract_sql() → SQL
         ↓
      validate_sql() [Guardrails applied]
         ↓
      execute_sql() [Against readonly role]
         ↓
      explain_result() [Generate English summary]
         ↓
      Return { sql, rows, explanation, row_count }
```

#### Key Components

**1. Schema Description** (lines 1-27)
```python
SCHEMA_DESCRIPTION = """
Tables:
employees(id, name, department, role, hire_date, salary, years_experience)
servers(id, hostname, environment, os, team)
incidents(...)
vulnerabilities(...)
"""
```
This is sent to LLM to guide SQL generation.

**2. SQL Generation** (lines 80-102)
```python
def generate_sql(question: str) -> str:
    # Build a prompt with schema + rules
    # Call Ollama qwen3:8b
    # Extract SQL from markdown code fence
    # Return cleaned SQL
```

**3. SQL Extraction** (lines 64-77)
Handles LLM responses that may include:
- Markdown fenced code blocks (```sql ... ```)
- Reasoning text before/after SQL
- Multiple code fence formats

**4. Guardrails - validate_sql()** (lines 125-162)

See [Security & Guardrails](#security--guardrails) section for detailed explanation.

**5. SQL Execution** (lines 165-178)
- Uses readonly database engine (separate credentials)
- Statement timeout: 5 seconds (line 21)
- Automatic ROLLBACK (connection is read-only anyway)
- Error handling for OperationalError (timeout + other errors)

**6. Result Explanation** (lines 181-204)
- LLM receives question + SQL + preview of top-20 rows
- Generates business-friendly 2-4 sentence summary
- No markdown or SQL repetition

#### Configuration
- LLM Model: qwen3:8b (line 14)
- Max rows: 200 (line 15)
- Query timeout: 5 seconds (line 16)
- Ollama endpoint: configurable via settings.ollama_base_url

### 4. RAG (Retrieval-Augmented Generation)

**File**: [rag.py](backend/app/rag.py) (lines 1-200)

**Purpose**: Answer questions about company policies and SOPs using document search + LLM.

#### Components

**1. Document Ingestion** (lines 77-108)
```python
def ingest_docs() -> int:
    # Reads all *.md from docs_corpus/
    # Chunks text (800 chars, 100 char overlap)
    # Embeds each chunk using Ollama nomic-embed-text
    # Stores in ChromaDB with metadata (source file, chunk index)
    # Returns count of chunks stored
```

**Document Source**: [docs_corpus/](backend/docs_corpus/)
- change_management_policy.md
- incident_management_sop.md
- vulnerability_management_policy.md

**2. Embedding** (lines 42-50)
- Model: nomic-embed-text (line 15)
- Dimensions: typically 768 (standard for nomic)
- Called via Ollama /api/embeddings endpoint

**3. Vector Store** (lines 51-55)
- ChromaDB PersistentClient
- Path: [backend/chroma_store/](backend/chroma_store/)
- Collection name: "enterprise_docs"
- Persists to disk automatically

**4. Retrieval** (lines 111-125)
```python
def retrieve(question: str, top_k: int = TOP_K) -> list[dict]:
    # Embed the user's question
    # Query ChromaDB for top-4 similar chunks
    # Return chunks with source file + distance score
```

**5. Answer Generation** (lines 144-167)
```python
def answer_from_docs(question: str) -> dict:
    # Retrieve top-4 chunks
    # Build context string with source citations
    # Ask LLM to answer using ONLY that context
    # LLM must cite sources
    # Return answer + sources with distance scores
```

#### Configuration
- Embed model: nomic-embed-text (line 15)
- Chat model: qwen3:8b (line 16)
- Chunk size: 800 characters (line 19)
- Chunk overlap: 100 characters (line 20)
- Top-k retrieval: 4 chunks (line 21)
- ChromaDB path: backend/chroma_store/ (line 17)

### 5. Agent Router (Hybrid Tool Selection)

**File**: [agent.py](backend/app/agent.py) (lines 1-120)

**Purpose**: Use LLM tool-calling to intelligently route between SQL and RAG based on question content.

#### Tool Definitions
Two tools exposed to the LLM:

**Tool 1: query_database**
```python
{
    "name": "query_database",
    "description": "Answer questions about employees, servers, incidents, vulnerabilities...",
    "parameters": {
        "type": "object",
        "properties": {"question": {"type": "string"}},
        "required": ["question"]
    }
}
```

**Tool 2: search_documents**
```python
{
    "name": "search_documents",
    "description": "Answer questions about company policies, SOPs, SLAs, processes...",
    "parameters": {
        "type": "object",
        "properties": {"question": {"type": "string"}},
        "required": ["question"]
    }
}
```

#### Decision Logic (lines 62-81)

```python
def _decide_tool(question: str) -> dict:
    # Send question + tools to Ollama (qwen3:8b)
    # LLM responds with tool_calls array
    # Extract first tool call
    # If no tool selected, default to query_database
    # Return { name: tool_name, arguments: {...} }
```

**Fallback Behavior**: If LLM doesn't select a tool, defaults to `query_database` (line 77).

#### Execution (lines 84-113)
```python
def run_agent(db: Session, question: str) -> dict:
    # Decide which tool
    # Call tool (search_documents or sql_ask)
    # Build unified response with:
    #   - tool_used
    #   - question
    #   - answer
    #   - SQL/sources (depending on tool)
    # Return JSON
```

#### Configuration
- LLM Model: qwen3:8b (line 15)
- Ollama chat endpoint: configurable via settings.ollama_base_url

### 6. MCP Server (Model Context Protocol)

**File**: [mcp_server.py](backend/app/mcp_server.py) (lines 1-70)

**Purpose**: Expose the same two tools (query_database, search_documents) via MCP protocol, allowing external MCP clients (Claude Desktop, other agents) to use these capabilities.

#### MCP Tool Definitions

**Tool 1: query_database**
- Accepts: question (str)
- Returns: { sql, rows, row_count, explanation }
- Uses: Text-to-SQL pipeline via sql_ask()

**Tool 2: search_documents**
- Accepts: question (str)
- Returns: { answer, sources }
- Uses: RAG via answer_from_docs()

#### Running the MCP Server
```bash
# Standalone execution (stdio transport)
python -m app.mcp_server
```

**Stdout/stderr transport**: Standard for local MCP clients to communicate via stdio.

#### Integration with Claude Desktop
MCP servers can be configured in `~/.config/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "aiops-assistant": {
      "command": "python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "/path/to/backend"
    }
  }
}
```

---

## Core Implementations

### SQL Query Guardrails Deep Dive

**File**: [text_to_sql.py](backend/app/text_to_sql.py) - Lines 125-162

#### Multi-Layer Security

**Layer 1: Statement Type Validation**
```python
def validate_sql(sql: str) -> str:
    # Only allow SELECT and WITH (CTEs)
    statements = sqlparse.parse(sql)
    if len(statements) != 1:
        raise UnsafeSQLError("Only a single SQL statement is allowed.")
    
    stmt_type = stmt.get_type()  # 'SELECT', 'UNKNOWN' (WITH)
    if stmt_type not in ALLOWED_STATEMENT_TYPES:
        raise UnsafeSQLError(f"Only SELECT queries are allowed (got {stmt_type}).")
```

**Allowed Types**: `{"SELECT", "UNKNOWN"}` (UNKNOWN covers WITH/CTEs)

**Layer 2: Text Prefix Check**
```python
    stripped = sql.strip().lower()
    if not (stripped.startswith("select") or stripped.startswith("with")):
        raise UnsafeSQLError("Only SELECT queries are allowed.")
```

**Layer 3: Forbidden Keyword Detection**
```python
FORBIDDEN_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|grant|revoke|create|"
    r"vacuum|copy|call|do|merge|refresh|reindex|comment|security|"
    r"pg_sleep|pg_terminate_backend|pg_cancel_backend)\b",
    re.IGNORECASE,
)

if FORBIDDEN_KEYWORDS.search(sql):
    raise UnsafeSQLError("Query contains a forbidden keyword.")
```

**Keywords Blocked**: 30+ dangerous operations including:
- Data modification: INSERT, UPDATE, DELETE
- Schema changes: ALTER, DROP, CREATE, TRUNCATE
- Permission changes: GRANT, REVOKE
- Denial-of-service: pg_sleep, pg_terminate_backend
- Advanced: VACUUM, COPY, CALL, DO, MERGE

**Layer 4: Multiple Statement Detection**
```python
    if ";" in sql.rstrip(";"):
        raise UnsafeSQLError("Multiple statements are not allowed.")
```

This prevents SQL injection via stacked queries.

**Layer 5: Automatic Row Limiting**
```python
def _ensure_row_limit(sql: str, max_rows: int = MAX_ROWS) -> str:
    # Parse SQL and check for existing LIMIT
    parsed = sqlparse.parse(sql)[0]
    tokens = [t for t in parsed.tokens if not t.is_whitespace]
    has_limit = any(t.ttype is sqlparse.tokens.Keyword and t.value.upper() == "LIMIT" for t in tokens)
    
    # If LIMIT exists, keep it; otherwise add MAX_ROWS (200)
    if has_limit:
        return sql_no_semicolon + ";"
    return f"{sql_no_semicolon} LIMIT {MAX_ROWS};"
```

**Impact**: Prevents full-table scans and DoS via large result sets.

#### Database-Level Guardrails

**File**: [db_init/01_create_reader_role.sql](db_init/01_create_reader_role.sql)

```sql
CREATE ROLE aiops_reader LOGIN PASSWORD 'readonly_dev_pw';
GRANT CONNECT ON DATABASE aiops TO aiops_reader;
GRANT USAGE ON SCHEMA public TO aiops_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO aiops_reader;
ALTER ROLE aiops_reader SET statement_timeout = '5s';
ALTER ROLE aiops_reader SET default_transaction_read_only = on;
```

**Key Features**:
1. **Separate role**: aiops_reader (not the app user)
2. **SELECT-only**: No INSERT/UPDATE/DELETE permissions
3. **Schema isolation**: Only public schema accessible
4. **Statement timeout**: 5-second hard limit
5. **Transaction read-only**: PostgreSQL enforces at role level

**Benefit**: Even if application validation is bypassed, database refuses modifications.

#### Execution Safety

**File**: [text_to_sql.py](backend/app/text_to_sql.py) - Lines 165-178

```python
def execute_sql(db: Session, sql: str) -> list[dict]:
    try:
        # Set statement timeout (redundant with role setting, but explicit)
        db.execute(text(f"SET LOCAL statement_timeout = '{QUERY_TIMEOUT_SECONDS}s'"))
        
        # Execute read-only query
        result = db.execute(text(sql))
        
        # Convert to JSON-safe dict list
        columns = result.keys()
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return rows
    except OperationalError as e:
        raise UnsafeSQLError(f"Query failed or timed out: {e}")
    finally:
        db.rollback()  # always discard; connection is read-only anyway
```

**Safety Features**:
1. Separate readonly_engine connection (different credentials)
2. Query timeout enforcement
3. Rollback on error to ensure clean state
4. OperationalError catches both timeout and other errors

---

## Security & Guardrails

### Authentication & Authorization

**Implementation**: [auth.py](backend/app/auth.py)

**Flow**:
1. User POSTs credentials to /api/login
2. Server checks against DEMO_USERNAME/DEMO_PASSWORD
3. Password validation uses bcrypt.checkpw() (never logs plaintext)
4. On success, server returns JWT access token
5. Client stores token in localStorage
6. Subsequent requests include `Authorization: Bearer <token>` header
7. FastAPI dependency get_current_user() validates token

**Token Details**:
- Algorithm: HS256 (HMAC-SHA256)
- Payload: { sub: username, exp: expiry_timestamp }
- Secret: JWT_SECRET from environment
- TTL: 60 minutes

**Development-Only Limitation**: Single hardcoded demo user. In production, would use:
- User database table
- Per-user password hashing
- Refresh tokens
- Session invalidation endpoints

### Data Access Control

**Read-Only Database Role**: [db_init/01_create_reader_role.sql](db_init/01_create_reader_role.sql)

The system maintains two database connections:

| Connection | User | Purpose | Permissions |
|-----------|------|---------|-------------|
| engine | aiops | Internal app logic | Full access to aiops database |
| readonly_engine | aiops_reader | LLM-generated SQL execution | SELECT only, 5s timeout |

**Rationale**: Even if LLM outputs malicious SQL, the database enforces read-only at the role level.

### Logging & Monitoring

**File**: [logging_config.py](backend/app/logging_config.py)

**JSON-Structured Logging**:
```json
{
  "timestamp": "2026-10-01T14:23:45+0000",
  "level": "INFO",
  "logger": "aiops",
  "message": "request completed",
  "request_id": "a7c3e9f2",
  "path": "/api/ask",
  "method": "POST",
  "status_code": 200,
  "duration_ms": 1234.56
}
```

**Benefits**:
- Single-line JSON for log aggregation (ELK, Datadog, etc.)
- Correlation IDs for request tracing
- Duration tracking for performance analysis
- Exception details included automatically

**Request Logging Middleware** (lines 43-72):
- Wraps every request with correlation ID
- Records path, method, status, duration
- Logs on completion or exception

---

## Database Design

### Schema

**File**: [models.py](backend/app/models.py)

#### Entity-Relationship Diagram
```
┌────────────────┐
│   employees    │
├────────────────┤
│ id (PK)        │
│ name           │
│ department     │
│ role           │
│ hire_date      │
│ salary         │
│ years_exp      │
└────────────────┘

┌────────────────┐         ┌──────────────────────┐
│    servers     │◄────┬───┤   incidents          │
├────────────────┤    │   ├──────────────────────┤
│ id (PK)        │    │   │ id (PK)              │
│ hostname       │    │   │ title                │
│ environment    │    │   │ severity (P1-P4)     │
│ os             │    │   │ status               │
│ team           │    │   │ team                 │
└────────────────┘    │   │ server_id (FK)       │
                      │   │ created_date         │
                      │   │ resolved_date        │
                      │   │ description          │
                      │   └──────────────────────┘
                      │
                      │   ┌──────────────────────┐
                      └───┤ vulnerabilities      │
                          ├──────────────────────┤
                          │ id (PK)              │
                          │ cve_id               │
                          │ severity             │
                          │ status               │
                          │ server_id (FK)       │
                          │ discovered_date      │
                          └──────────────────────┘
```

### Table Definitions

**employees**
```python
class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    department = Column(String, nullable=False)  # Engineering, Security, etc.
    role = Column(String, nullable=False)        # Engineer, Lead, Manager
    hire_date = Column(Date, nullable=False)
    salary = Column(Numeric, nullable=False)     # In base units (e.g., rupees)
    years_experience = Column(Integer, nullable=False)
```

**servers**
```python
class Server(Base):
    __tablename__ = "servers"
    id = Column(Integer, primary_key=True)
    hostname = Column(String, nullable=False, unique=True)
    environment = Column(String, nullable=False)  # 'prod', 'staging', 'dev'
    os = Column(String, nullable=False)           # 'RHEL 8', 'Ubuntu 22.04', etc.
    team = Column(String, nullable=False)         # 'Linux Team', 'Windows Team'
    
    # Relationships
    vulnerabilities = relationship("Vulnerability", back_populates="server")
    incidents = relationship("Incident", back_populates="server")
```

**incidents**
```python
class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    severity = Column(String, nullable=False)     # 'P1', 'P2', 'P3', 'P4'
    status = Column(String, nullable=False)       # 'open', 'in_progress', 'resolved'
    team = Column(String, nullable=False)
    server_id = Column(Integer, ForeignKey("servers.id"))
    created_date = Column(Date, nullable=False)
    resolved_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    
    # Relationship
    server = relationship("Server", back_populates="incidents")
```

**vulnerabilities**
```python
class Vulnerability(Base):
    __tablename__ = "vulnerabilities"
    id = Column(Integer, primary_key=True)
    cve_id = Column(String, nullable=False)       # 'CVE-2024-1001'
    severity = Column(String, nullable=False)     # 'Critical', 'High', 'Medium', 'Low'
    status = Column(String, nullable=False)       # 'open', 'remediated'
    server_id = Column(Integer, ForeignKey("servers.id"))
    discovered_date = Column(Date, nullable=False)
    
    # Relationship
    server = relationship("Server", back_populates="vulnerabilities")
```

### Sample Queries Supported

The schema supports typical enterprise operations queries:

```sql
-- Count critical vulnerabilities
SELECT COUNT(*) FROM vulnerabilities 
WHERE severity='Critical' AND status='open';

-- Find employees by salary & experience
SELECT name, department, salary FROM employees 
WHERE salary > 1500000 AND years_experience >= 5;

-- Incidents by team
SELECT team, COUNT(*) as incident_count 
FROM incidents WHERE status='open' 
GROUP BY team;

-- Server vulnerabilities breakdown
SELECT s.hostname, COUNT(*) as vuln_count 
FROM servers s 
LEFT JOIN vulnerabilities v ON s.id = v.server_id 
WHERE v.status='open' 
GROUP BY s.id, s.hostname;

-- Join across incidents, servers, teams
SELECT i.title, s.hostname, s.environment 
FROM incidents i 
JOIN servers s ON i.server_id = s.id 
WHERE i.severity='P1' AND i.status='open';
```

### Database Initialization

**File**: [seed.py](backend/app/seed.py)

**Execution**: `python -m app.seed`

**Process**:
1. Drop all existing tables (clean slate)
2. Create all tables from SQLAlchemy models
3. Generate realistic sample data:
   - 40 employees with random names, departments, salaries
   - 25 servers with various OS/environments
   - 60 incidents linked to servers
   - 80 vulnerabilities linked to servers

**Sample Data Generation**:
```python
def seed():
    Base.metadata.drop_all(bind=engine)  # Clean
    Base.metadata.create_all(bind=engine)  # Create
    
    db = SessionLocal()
    try:
        # Generate employees, servers, incidents, vulnerabilities
        # Use realistic distributions and faker-like names
    finally:
        db.close()
```

---

## Integration Points

### 1. Frontend ↔ Backend Communication

**Protocol**: HTTP/JSON over CORS

**CORS Configuration** (main.py, lines 18-23):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Request/Response Example**:

**Request** (POST /api/agent):
```json
{
  "question": "How many critical vulnerabilities are open?"
}

Headers:
  Content-Type: application/json
  Authorization: Bearer eyJhbGc...
```

**Response** (200 OK):
```json
{
  "tool_used": "query_database",
  "question": "How many critical vulnerabilities are open?",
  "answer": "There are currently 12 critical vulnerabilities across our infrastructure...",
  "sql": "SELECT COUNT(*) as count FROM vulnerabilities WHERE severity='Critical' AND status='open'",
  "rows": [{"count": 12}],
  "row_count": 1
}
```

### 2. Backend ↔ Ollama Communication

**Protocol**: HTTP/JSON (Ollama API)

**Endpoints Used**:
- `/api/generate` - Text generation (LLM)
- `/api/chat` - Chat with tool-calling (Agent)
- `/api/embeddings` - Text embeddings (RAG)

**Example: SQL Generation Request**
```http
POST http://localhost:11434/api/generate

{
  "model": "qwen3:8b",
  "prompt": "You are a PostgreSQL expert...\nQuestion: How many employees...",
  "stream": false
}
```

**Example: Embedding Request**
```http
POST http://localhost:11434/api/embeddings

{
  "model": "nomic-embed-text",
  "prompt": "What is the incident response procedure?"
}
```

**Configuration** (config.py):
```python
class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    # When running in Docker: http://host.containers.internal:11434
```

### 3. Backend ↔ PostgreSQL Communication

**Protocol**: psycopg2 (PostgreSQL wire protocol)

**Connection Strings** (config.py):
```python
# App connections (full access)
database_url: str = "postgresql+psycopg2://localhost:5432/aiops"

# Readonly for LLM-generated SQL (restricted)
readonly_database_url: str = "postgresql+psycopg2://aiops_reader:readonly_dev_pw@localhost:5432/aiops"
```

**Connection Pool Management** (db.py):
```python
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

readonly_engine = create_engine(settings.readonly_database_url, pool_pre_ping=True)
ReadOnlySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=readonly_engine)
```

**pool_pre_ping=True**: Sends a ping before using a connection from the pool to ensure it's still alive.

### 4. Backend ↔ ChromaDB Integration

**Location**: backend/chroma_store/ (persistent disk storage)

**Lifecycle**:
1. **Initialization**: `ingest_docs()` called manually (see setup section)
2. **Retrieval**: `retrieve(question)` called on every RAG query
3. **Persistence**: Automatically saved to disk

**File Structure**:
```
backend/
└── chroma_store/
    ├── chroma.sqlite3          # ChromaDB metadata
    └── 459ca896-59fb-4572.../ # Collection data
```

### 5. Docker Compose Orchestration

**File**: [docker-compose.yml](docker-compose.yml)

**Services**:

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| postgres | postgres:16-alpine | 5433 → 5432 | Database server |
| backend | ./backend (Dockerfile) | 8000 | FastAPI app |
| frontend | ./frontend (Dockerfile) | 3000 | Next.js app |

**Network**: aiops-net (bridge)

**Key Configuration**:
- Backend depends_on postgres (with healthcheck)
- Environment variables passed to backend:
  - DATABASE_URL (app user)
  - READONLY_DATABASE_URL (reader user)
  - OLLAMA_BASE_URL (host.containers.internal:11434 for Docker)

---

## Use Cases & Testing

### 1. Implemented Use Cases

#### Use Case 1: Operational Analytics
**User Question**: "Show employees earning more than 15 lakh with 5+ years experience"

**Expected Flow**:
1. Agent receives question
2. LLM decides: Text-to-SQL (data query)
3. SQL generated: SELECT name, salary, years_experience FROM employees WHERE salary > 1500000 AND years_experience >= 5
4. Guardrails validate (single SELECT, row limit 200)
5. Execute against readonly role
6. Return 5-15 rows with salaries + experience
7. LLM explains: "I found X employees in your organization..."

**Tools Used**: text_to_sql.py (SQL generation + guardrails)

#### Use Case 2: Security Intelligence
**User Question**: "How many critical vulnerabilities are currently open?"

**Expected Flow**:
1. Agent decides: Text-to-SQL
2. SQL: SELECT COUNT(*) FROM vulnerabilities WHERE severity='Critical' AND status='open'
3. Execute, return count
4. LLM explains: "There are X critical vulnerabilities that need immediate attention..."

**Tools Used**: text_to_sql.py

#### Use Case 3: Policy/Procedure Lookup
**User Question**: "What is the procedure for a P1 incident?"

**Expected Flow**:
1. Agent decides: search_documents (not a data query)
2. Embed question using nomic-embed-text
3. Retrieve top-4 similar chunks from incident_management_sop.md
4. Build context from chunks
5. LLM answers using only context
6. Return answer + source (incident_management_sop.md)

**Tools Used**: rag.py (document retrieval + RAG)

#### Use Case 4: SLA Verification
**User Question**: "What are the SLA timelines for remediating vulnerabilities?"

**Expected Flow**:
1. Agent decides: search_documents (policy question)
2. ChromaDB retrieves from vulnerability_management_policy.md
3. LLM cites specific sections
4. Return timelines + source document

**Tools Used**: rag.py

#### Use Case 5: Incident Triaging
**User Question**: "Which team has the most open incidents?"

**Expected Flow**:
1. Agent decides: Text-to-SQL
2. SQL: SELECT team, COUNT(*) as count FROM incidents WHERE status='open' GROUP BY team ORDER BY count DESC LIMIT 1
3. Execute, return team + count
4. LLM explains: "Team X is managing X open incidents currently..."

**Tools Used**: text_to_sql.py

### 2. Test Coverage

**File**: [backend/tests/test_text_to_sql_guardrails.py](backend/tests/test_text_to_sql_guardrails.py)

**Test Suite**: Guardrails validation (pure, deterministic)

**Tests Implemented**:

```python
def test_allows_simple_select():
    # ✓ SELECT * FROM employees → adds LIMIT
    
def test_allows_with_cte():
    # ✓ WITH x AS (...) SELECT ... → adds LIMIT
    
def test_preserves_existing_limit():
    # ✓ SELECT ... LIMIT 5 → keeps as LIMIT 5 (not overridden)
    
def test_adds_default_limit_when_missing():
    # ✓ SELECT ... → adds LIMIT 200
    
def test_blocks_destructive_statements():
    # ✓ DELETE FROM ... → raises UnsafeSQLError
    # ✓ UPDATE ... SET ... → raises UnsafeSQLError
    # ✓ DROP TABLE ... → raises UnsafeSQLError
    # ✓ INSERT INTO ... → raises UnsafeSQLError
    # ✓ TRUNCATE ... → raises UnsafeSQLError
    # ✓ ALTER TABLE ... → raises UnsafeSQLError
    
def test_blocks_multiple_statements():
    # ✓ SELECT ...; DROP TABLE ... → raises UnsafeSQLError
    
def test_blocks_dos_patterns():
    # ✓ SELECT pg_sleep(100) → raises UnsafeSQLError
    
def test_blocks_non_select_statement_type():
    # ✓ EXPLAIN SELECT ... → raises UnsafeSQLError
```

**Run Tests**:
```bash
cd backend
python -m pytest tests/test_text_to_sql_guardrails.py -v
```

### 3. Manual Testing Scenarios

**Frontend Chat Interface Tests**:
1. ✓ Login with demo credentials → redirects to chat
2. ✓ Submit question → loads spinner, displays result
3. ✓ View SQL query in result card
4. ✓ View citations for document search results
5. ✓ Logout → clears token, shows login form

**Backend API Tests** (curl):

```bash
# Health check
curl http://localhost:8000/health

# DB health
curl http://localhost:8000/health/db

# Login
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "changeme123"}'

# Ask (requires token)
curl -X POST http://localhost:8000/api/agent \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question": "How many employees?"}'
```

**LLM Integration Tests**:
1. Ollama is running on localhost:11434
2. qwen3:8b model is pulled
3. nomic-embed-text model is pulled
4. Models respond within 120-second timeout

---

## Important Design Decisions

### 1. Separate Readonly Database Role

**Decision**: Maintain two database connections (app user + reader role)

**Rationale**:
- **Defense in depth**: Even if SQL validation is bypassed, database refuses modifications
- **Principle of least privilege**: LLM gets only what it needs (SELECT)
- **Audit trail**: All LLM queries run as aiops_reader role (auditable separately)
- **Role-based timeout**: Database enforces 5-second timeout at role level, not just in code

**Trade-off**: Requires DDL to set up reader role, slightly more complex deployment

**Alternative Considered**: Single role with table-level permissions (less secure)

### 2. Text-to-SQL with Multi-Layer Guardrails

**Decision**: Don't rely on a single validation mechanism

**Implemented Layers**:
1. Statement type validation (sqlparse)
2. Text prefix check (simple regex)
3. Forbidden keyword detection (regex)
4. Multiple statement detection (string parsing)
5. Row limiting (automatic LIMIT injection)
6. Database-level read-only enforcement

**Rationale**: LLMs can be unpredictable. Layered guardrails catch edge cases.

**Trade-off**: Performance cost of parsing/validation is negligible compared to LLM call (which takes seconds)

### 3. Agent Routing Over Separate Endpoints

**Decision**: Provide /api/agent that decides between SQL and RAG, plus separate /api/ask and /api/ask-docs

**Rationale**:
- Single unified endpoint (/api/agent) simplifies frontend
- LLM naturally selects the right tool via tool-calling
- Falls back to SQL if unclear (safe default)
- Separate endpoints available for advanced use cases

**Alternative Considered**: Always use agent (but adds latency for questions where tool is obvious)

### 4. Local Ollama Models (No Cloud)

**Decision**: All LLM computation happens on local Ollama

**Rationale**:
- No API costs (cost-free for demos/portfolio)
- No dependency on external services
- Data stays local (sensitive enterprise data)
- Demonstrates full-stack capability

**Trade-off**: Quality depends on local hardware; qwen3:8b is smaller model vs. GPT-4

**Alternative Considered**: OpenAI/Anthropic APIs (but costs $$, requires keys)

### 5. ChromaDB for Vector Storage

**Decision**: Use local ChromaDB instead of pinecone/weaviate

**Rationale**:
- No managed service dependency
- Embedded persistence (SQLite backend)
- Zero cost, zero latency
- Portable (data travels with code)

**Trade-off**: Not suitable for massive scale (>million documents), but fine for policy docs

### 6. PostgreSQL Over NoSQL

**Decision**: Structured relational database for operational data

**Rationale**:
- Enterprise data is highly structured (employees, servers, incidents)
- ACID guarantees important for operational queries
- Text-to-SQL pattern requires predefined schema
- Security model (roles, permissions) well-established

**Trade-off**: Less flexible for unstructured logs/traces (would use LogDB separately in production)

### 7. JWT Tokens Over Sessions

**Decision**: Stateless JWT tokens for authentication

**Rationale**:
- Stateless (no session storage required)
- Scalable (can distribute across multiple servers)
- Simple for single-user demo (not much state)
- Token validates on every request (no session lookup)

**Trade-off**: No server-side token revocation (not critical for demo)

### 8. MCP Server for External Integration

**Decision**: Expose tools via Model Context Protocol for external clients

**Rationale**:
- Claude Desktop can use these tools natively
- Any MCP-compatible client (future agents) can integrate
- Separate from FastAPI (don't block main API)
- Demonstrates protocol fluency

**Trade-off**: Requires running separate MCP process (but stdio transport is simple)

---

## Deployment Architecture

### Local Development Setup

**Prerequisites** (already installed):
- PostgreSQL 16 (brew service)
- Node.js (homebrew)
- Python 3.14 (homebrew)
- Ollama (app) running locally

**Directory Structure**:
```
fullstack-ai-assistant/
├── backend/               # Python FastAPI app
│   ├── app/              # Source code
│   │   ├── main.py
│   │   ├── agent.py
│   │   ├── text_to_sql.py
│   │   ├── rag.py
│   │   ├── auth.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── mcp_server.py
│   │   ├── config.py
│   │   ├── logging_config.py
│   │   └── seed.py
│   ├── tests/            # pytest tests
│   ├── docs_corpus/      # RAG documents
│   ├── chroma_store/     # Vector DB (generated)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env (dev config)
│
├── frontend/             # Next.js React app
│   ├── src/app/
│   │   ├── page.tsx      # Chat UI
│   │   ├── LoginForm.tsx # Auth
│   │   ├── ResultCard.tsx # Result display
│   │   └── types.ts      # TS types
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   └── Dockerfile
│
├── db_init/              # Database initialization SQL
│   └── 01_create_reader_role.sql
│
├── docker-compose.yml    # Container orchestration
└── README.md
```

### Docker Compose Deployment

**File**: [docker-compose.yml](docker-compose.yml)

**Start Containers**:
```bash
docker-compose up --build
```

**Services Started**:
1. postgres (port 5433)
2. backend (port 8000)
3. frontend (port 3000)

**Prerequisites**:
- Ollama running on host (port 11434)
- Backend connects via host.containers.internal:11434

**Database Initialization**:
```bash
# After containers are running
docker-compose exec backend python -m app.seed
```

**Logs**:
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Environment Configuration

**Backend .env** (development):
```
DATABASE_URL=postgresql+psycopg2://aiops:aiops_dev_pw@localhost:5432/aiops
READONLY_DATABASE_URL=postgresql+psycopg2://aiops_reader:readonly_dev_pw@localhost:5432/aiops
APP_ENV=development
JWT_SECRET=dev-only-insecure-secret-change-me
DEMO_USERNAME=admin
DEMO_PASSWORD=changeme123
OLLAMA_BASE_URL=http://localhost:11434
```

**Frontend .env** (development):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Production Considerations (Not Implemented)

1. **Authentication**:
   - Move to real user database
   - Implement OAuth2/SAML if needed
   - Add session revocation endpoints

2. **Database**:
   - Use managed PostgreSQL (RDS, Cloud SQL)
   - Enable SSL connections
   - Configure read replicas for analytics

3. **LLM**:
   - Could switch to cloud LLM (OpenAI, Bedrock)
   - Implement token counting and rate limiting
   - Add prompt versioning/A-B testing

4. **Vector Store**:
   - Move to managed Pinecone/Weaviate at scale
   - Implement reranking for retrieval quality

5. **Frontend**:
   - Add error boundaries and monitoring (Sentry)
   - Implement analytics (Mixpanel, Amplitude)
   - Add PWA capabilities

6. **Deployment**:
   - Kubernetes for container orchestration
   - CI/CD pipeline (GitHub Actions, GitLab)
   - Automated testing (unit, integration, E2E)

---

## Summary: 30-Second Overview

**What This Is**: A fullstack AI application for querying an enterprise operational database and searching policy documents using natural language.

**How It Works**:
1. User logs in (JWT auth)
2. Types a question in the chat UI
3. Backend receives question
4. Agent LLM decides: SQL database query or document search?
5. If SQL: generate SQL → validate (guardrails) → execute (readonly role) → explain
6. If documents: embed question → search ChromaDB → retrieve top-4 chunks → generate answer with citations
7. Return result to frontend

**Key Security Features**:
- Guardrails on LLM-generated SQL (5 layers)
- Readonly database role (6th layer)
- JWT authentication
- CORS restricted to frontend origin
- JSON structured logging with correlation IDs

**Technologies**: FastAPI, Next.js, PostgreSQL, Ollama (local LLM), ChromaDB, SQLAlchemy, SQLparse

**Sample Questions Supported**:
- "Show employees earning 15+ lakh with 5+ years experience"
- "How many critical vulnerabilities are open?"
- "What is the P1 incident procedure?"
- "What are vulnerability remediation SLAs?"

**Extensibility**: MCP server interface allows Claude Desktop and other agents to use the same tools.

---

## Quick Reference: Where Things Are

| Topic | File | Lines |
|-------|------|-------|
| API endpoints | [main.py](backend/app/main.py) | 1-120 |
| Agent routing logic | [agent.py](backend/app/agent.py) | 1-120 |
| Text-to-SQL guardrails | [text_to_sql.py](backend/app/text_to_sql.py) | 125-162 |
| RAG document retrieval | [rag.py](backend/app/rag.py) | 111-167 |
| Authentication | [auth.py](backend/app/auth.py) | 1-60 |
| Database schema | [models.py](backend/app/models.py) | 1-70 |
| Database setup | [db.py](backend/app/db.py) | 1-40 |
| Sample data seeding | [seed.py](backend/app/seed.py) | 1-100+ |
| Reader role setup | [01_create_reader_role.sql](db_init/01_create_reader_role.sql) | 1-20 |
| MCP server | [mcp_server.py](backend/app/mcp_server.py) | 1-70 |
| Logging config | [logging_config.py](backend/app/logging_config.py) | 1-80 |
| Frontend chat UI | [page.tsx](frontend/src/app/page.tsx) | 1-150 |
| Tests | [test_text_to_sql_guardrails.py](backend/tests/test_text_to_sql_guardrails.py) | 1-100+ |
| Docker setup | [docker-compose.yml](docker-compose.yml) | 1-100+ |

