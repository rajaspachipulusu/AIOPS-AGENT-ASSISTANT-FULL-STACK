# EXECUTION FLOW GUIDE: Step-by-Step with Learning Points

This document provides the **exact sequence** of what to execute, in what order, and the key learning points from each step.

---

## PHASE 1: PREREQUISITES VERIFICATION (5 minutes)

### Step 1.1: Verify Python 3.14 Installation
```bash
/opt/homebrew/bin/python3.14 --version
```
**Expected Output**: `Python 3.14.x`

**Why This Matters**: The backend requires Python 3.14. The default shell PATH doesn't include `/opt/homebrew/bin`, so we use the full path here and in subsequent commands.

**Learning Point**: Modern Python versions introduce breaking changes (e.g., walrus operator := in 3.8, structural pattern matching in 3.10). Always verify the exact version matches requirements.

---

### Step 1.2: Verify Node.js Installation
```bash
/opt/homebrew/bin/node --version
```
**Expected Output**: `v20.x.x` or higher

**Why This Matters**: Frontend build and dev server require Node.js. Next.js 16.3.8 has specific version compatibility.

**Learning Point**: Node.js and npm are separate; npm comes bundled. Always verify both work: `npm --version`.

---

### Step 1.3: Verify PostgreSQL Service Running
```bash
brew services list | grep postgres
```
**Expected Output**: Shows `postgresql` as `started`

**If NOT running**, start it:
```bash
brew services start postgresql@16
```

**Why This Matters**: PostgreSQL must be running **before** backend initialization. The seed script will fail if the database server is unreachable.

**Learning Point**: Database initialization is **not idempotent** by default. `python -m app.seed` drops and recreates tables, so multiple runs are safe, but the database must exist first.

**Verify Connectivity**:
```bash
psql -U postgres -c "SELECT version();"
```
**Expected Output**: PostgreSQL version info (should be 16.x)

---

### Step 1.4: Verify Ollama Running with Required Models
```bash
curl http://localhost:11434/api/tags
```
**Expected Output**: JSON listing installed models, including `qwen3:8b` and `nomic-embed-text`

**If Ollama is NOT running**, start it:
```bash
ollama serve  # or: open -a Ollama  (if installed as app on Mac)
```

**If models are missing**, pull them:
```bash
ollama pull qwen3:8b
ollama pull nomic-embed-text
```
**Note**: Each pull takes 10-30 minutes depending on internet speed. Do this **once** and they persist.

**Why This Matters**: 
- `qwen3:8b` is used for SQL generation, LLM explanations, and agent routing decisions
- `nomic-embed-text` is used for embedding documents and questions for RAG
- If either model is missing, API calls to Ollama will fail with unclear errors

**Learning Point**: Ollama is a **local model server**. It keeps models loaded in GPU/CPU memory. If you run multiple models, you need sufficient VRAM. For `qwen3:8b` + `nomic-embed-text`, typically 16GB VRAM is sufficient. Ollama starts slowly (10-30 seconds); always verify with `curl` before proceeding.

---

## PHASE 2: BACKEND INITIALIZATION (20 minutes)

### Step 2.1: Navigate to Backend Directory
```bash
cd /Users/rajas.pr/fullstack-ai-assistant/backend
```

**Learning Point**: From here on, all paths are relative to this directory.

---

### Step 2.2: Create Python Virtual Environment
```bash
/opt/homebrew/bin/python3.14 -m venv .venv
```
**Expected Output**: A new `.venv/` directory is created.

**Why This Matters**: Virtual environments isolate project dependencies from system Python. This prevents version conflicts with other Python projects on your machine.

**Learning Point**: 
- `.venv` is a **directory**, not a script. It contains Python binaries, site-packages, and activation scripts.
- Different projects can have different versions of the same package (e.g., one uses Django 3.2, another uses 4.0).
- Always use the full path `/opt/homebrew/bin/python3.14` when creating a venv. Future Python commands will use the venv's Python automatically.

---

### Step 2.3: Activate Virtual Environment
```bash
source .venv/bin/activate
```
**Expected Output**: Shell prompt now shows `(.venv) $` prefix.

**Why This Matters**: Activating the venv modifies your shell's PATH. Now `python` command refers to `.venv/bin/python`, not system Python. All package installations go to `.venv/site-packages`.

**Learning Point**: Activation is **temporary** per shell session. If you open a new terminal tab, you must run `source .venv/bin/activate` again. This is why production deployments use `python -m` syntax or explicit paths instead of relying on activation.

---

### Step 2.4: Install Dependencies
```bash
pip install -r requirements.txt
```
**Expected Output**: Installs 100+ packages, finishes with "Successfully installed..."

**What Gets Installed**:
- **fastapi** (0.142.2) - web framework
- **sqlalchemy** (2.1.1) - ORM
- **psycopg2-binary** (2.9.13) - PostgreSQL driver
- **pydantic** (2.13.5) - validation
- **chromadb** (1.5.9) - vector store
- **mcp** (2.2.0) - Model Context Protocol
- **pytest** (9.1.1) - testing
- **pyjwt** (2.15.1) - JWT tokens
- **requests** (2.34.2) - HTTP client
- ... 90+ more packages

**Why This Matters**: `requirements.txt` pins exact versions. This ensures reproducibility: the code runs the same on your machine and on CI/production.

**Learning Point**: 
- `pip install -r requirements.txt` is **deterministic** only if `requirements.txt` uses pinned versions (`==`). If you see `>=` or `~=`, multiple installs might get different versions.
- After install, run `pip freeze > requirements.txt` to lock all transitive dependencies. The current `requirements.txt` already does this.
- Installation time: 3-5 minutes typically. Do NOT interrupt; pip might leave packages in an inconsistent state.

---

### Step 2.5: Verify Installation
```bash
python -c "import sqlalchemy, fastapi, pydantic; print('✓ Core packages installed')"
```
**Expected Output**: `✓ Core packages installed` (no errors)

**Why This Matters**: Quickly confirms the venv is functional and key packages are importable.

**Learning Point**: 
- `python -c` executes a Python snippet without creating a file. Useful for quick verification.
- If this command fails, try running `pip install -r requirements.txt` again. Sometimes network interruptions cause incomplete installs.

---

### Step 2.6: Create Database Roles (First Time Only)
```bash
psql -U postgres -d aiops -f db_init/01_create_reader_role.sql
```
**Expected Output**:
```
DO
GRANT
GRANT
GRANT
ALTER ROLE
```
(No errors)

**What This Does**:
1. Checks if `aiops_reader` role exists; if not, creates it
2. Grants CONNECT permission to aiops database
3. Grants USAGE on public schema
4. Grants SELECT-only on all tables (now and future)
5. Sets 5-second statement timeout for this role
6. Enables read-only mode for this role

**Why This Matters**: This is the **security foundation**. Even if an LLM-generated SQL query somehow passes validation, the `aiops_reader` role can only SELECT, never INSERT/UPDATE/DELETE.

**Learning Point**: 
- SQL roles in PostgreSQL are like Unix users: they have specific permissions
- `ALTER DEFAULT PRIVILEGES` ensures **future** tables created in the schema automatically grant SELECT to this role (prevents needing to re-run this script after new tables are added)
- Statement timeout (`5s`) is a **DOS protection**: prevents someone from running an expensive query that locks tables for hours

**How to Verify**:
```bash
psql -U postgres -d aiops -c "SELECT rolname, rolcanlogin, rolsuper FROM pg_roles WHERE rolname = 'aiops_reader';"
```
**Expected Output**: Row showing `aiops_reader | t | f` (can login, NOT superuser)

---

### Step 2.7: Seed Sample Data (First Time, or to Reset)
```bash
python -m app.seed
```
**Expected Output**:
```
Generating sample employees, servers, incidents, and vulnerabilities...
Seeding complete. ✓
```

**What Happens**:
1. Drops all existing tables (if any)
2. Creates tables from SQLAlchemy models:
   - `employees` (40 rows)
   - `servers` (25 rows)
   - `incidents` (60 rows)
   - `vulnerabilities` (80 rows)
3. Creates foreign key relationships
4. Commits to database

**Sample Data Generated**:
- **Employees**: Random names (Arjun Sharma, Priya Patel, etc.), departments (Engineering, Security, Infrastructure), roles, hire dates (2015-2024), salaries (600k-2.5M INR), years_experience
- **Servers**: hostnames (PROD-100, STG-101, DEV-102), environments (prod/staging/dev), OS (RHEL, Ubuntu, Windows), teams
- **Incidents**: titles (e.g., "High CPU on PROD-102"), severity (P1/P2/P3/P4), status (open/in_progress/resolved), created dates (2023-2025), resolved dates (if closed)
- **Vulnerabilities**: CVE IDs (CVE-2024-1000+), severity (Critical/High/Medium/Low), status (open/remediated), related servers

**Why This Matters**: The sample data allows testing realistic Text-to-SQL queries without needing a real database. Example queries:
- "How many critical vulnerabilities are currently open?" (aggregation)
- "Show employees earning more than 15 lakh with 5+ years experience" (filtering)
- "Which team has the most open incidents?" (joins + group by)

**Learning Point**: 
- The `seed()` function is **deterministic** except for date randomization. Multiple runs generate different dates but same counts (40 employees, etc.).
- This data is **ephemeral**: each run drops and recreates. For persistent test data, add a `--preserve` flag or modify the seed function.
- The data distribution is realistic: incidents mostly in prod, vulnerabilities increasing over time, employees spread across departments.

**How to Verify**:
```bash
psql -U rajas.pr -d aiops -c "SELECT COUNT(*) FROM employees; SELECT COUNT(*) FROM servers; SELECT COUNT(*) FROM incidents; SELECT COUNT(*) FROM vulnerabilities;"
```
**Expected Output**: `40 | 25 | 60 | 80`

---

### Step 2.8: Ingest RAG Documents
```bash
python -c "from app.rag import ingest_docs; chunks = ingest_docs(); print(f'✓ Ingested {chunks} chunks from docs_corpus/')"
```
**Expected Output**: `✓ Ingested 47 chunks from docs_corpus/` (or similar)

**What Happens**:
1. Reads all `.md` files from `backend/docs_corpus/`:
   - `change_management_policy.md`
   - `incident_management_sop.md`
   - `vulnerability_management_policy.md`
2. Chunks each document (800 chars/chunk, 100-char overlap)
3. Embeds each chunk using Ollama `nomic-embed-text` model
   - This involves **network calls** to Ollama (local)
   - Each chunk embedding takes 1-2 seconds
4. Stores embeddings + metadata in ChromaDB persistent store (`backend/chroma_store/`)

**Why This Matters**: RAG (Retrieval-Augmented Generation) allows the LLM to answer questions about **company policies and procedures** by retrieving relevant document chunks and grounding the answer in them. Without this step, the LLM would only have its training data, which might be outdated or inaccurate.

**Learning Point**: 
- **Embedding** is the process of converting text to a dense vector (e.g., 768 dimensions for `nomic-embed-text`). Semantically similar text produces similar vectors.
- **Chunking** is necessary because Ollama can't embed long documents in one call (context limit). The overlap (100 chars) ensures concepts at chunk boundaries aren't lost.
- **ChromaDB** stores embeddings + original text + metadata. At query time, it computes similarity between the question embedding and all chunk embeddings, returning top-k most similar.
- Ingestion is **deterministic**: same documents → same chunks → same embeddings. Useful for reproducibility.
- If you edit a document in `docs_corpus/`, you must re-run `ingest_docs()` to update the vector store.

**How to Verify**:
```bash
python -c "from app.rag import _get_collection; c = _get_collection(); print(f'✓ {len(c.get()[\"ids\"])} chunks in ChromaDB')"
```
**Expected Output**: `✓ 47 chunks in ChromaDB` (or your count)

---

## PHASE 3: START BACKEND API (2 minutes)

### Step 3.1: Start Uvicorn Server
```bash
uvicorn app.main:app --port 8000 --reload
```
**Expected Output**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

**What This Does**:
1. Loads the FastAPI app from `app/main.py`
2. Binds to port 8000
3. Enables `--reload` (automatic restart on file changes)
4. Logs all requests to stdout

**Available Endpoints** (immediately):
- `GET /health` → `{"status": "ok"}`
- `GET /health/db` → `{"db": "ok"}`
- `GET /docs` → Swagger UI (browser)
- `GET /openapi.json` → OpenAPI schema (machine-readable)
- `POST /api/login` → authenticate and get JWT token
- `POST /api/ask` → direct Text-to-SQL
- `POST /api/ask-docs` → direct RAG search
- `POST /api/agent` → hybrid routing (SQL vs RAG)

**Why This Matters**: The backend is now **live**. Frontend and external clients can make HTTP requests to it.

**Learning Point**: 
- `--reload` is for **development only**. It imports the app on every request to pick up changes, which is slow and can cause issues. For production, use a process manager like Gunicorn or uvicorn without `--reload`.
- Logging shows request method, path, status code, response time. Watch this output to debug API issues.
- If you see `ERROR: Uvicorn server crashed with exit code 1`, there's a Python syntax error or import error in `app/main.py` or its dependencies. Check the traceback.

**Test the Backend**:
```bash
# In a new terminal
curl http://localhost:8000/health
```
**Expected Output**: `{"status":"ok"}`

```bash
curl http://localhost:8000/health/db
```
**Expected Output**: `{"db":"ok"}` (confirms database connectivity)

---

### Step 3.2: Keep Backend Running
**Do NOT stop the backend.** Keep the terminal running with the Uvicorn server. If you need a new terminal, open a new tab.

**Why This Matters**: The backend must stay running for the frontend and user interactions to work. Stopping it breaks all API calls.

**Learning Point**: In production, use a terminal multiplexer like `tmux` or `screen` to run multiple long-running processes. Or use `systemd` units or Docker to manage process lifecycle.

---

## PHASE 4: FRONTEND INITIALIZATION & STARTUP (10 minutes)

### Step 4.1: Open New Terminal Tab
Keep the backend running in the previous tab. **Open a new terminal tab** and navigate to the frontend directory.

```bash
cd /Users/rajas.pr/fullstack-ai-assistant/frontend
```

**Learning Point**: Never stop a running server unless intentional. Open new terminals instead.

---

### Step 4.2: Install Node.js Dependencies
```bash
/opt/homebrew/bin/npm install
```
**Expected Output**: Installs 200+ packages, shows dependency tree, finishes with "added X packages".

**What Gets Installed**:
- **next** (16.3.8) - React framework
- **react** (19.2.8) - UI library
- **react-dom** (19.2.8) - React rendering
- **typescript** (5.x) - Type checking
- **tailwindcss** (4.x) - CSS framework
- **eslint** (9.x) - Linter

**Why This Matters**: These are the dependencies needed to build and run the Next.js frontend.

**Learning Point**: 
- `npm install` reads `package.json`, downloads packages from npm registry, and stores them in `node_modules/`.
- First install takes 2-3 minutes. Subsequent installs are much faster (cache).
- `npm ci` (clean install) is recommended for CI/production: it uses `package-lock.json` (exact versions) instead of potentially upgrading patch versions.

**Verify Installation**:
```bash
/opt/homebrew/bin/npm --version
```
**Expected Output**: `10.x.x` or higher

---

### Step 4.3: Start Next.js Dev Server
```bash
/opt/homebrew/bin/npm run dev
```
**Expected Output**:
```
▲ Next.js 16.3.8
- Local: http://localhost:3000
- Environments: .env.local
```

**What This Does**:
1. Starts a development server on port 3000
2. Watches for file changes (hot module reloading)
3. Compiles TypeScript on the fly
4. Serves the UI in the browser

**Why This Matters**: The frontend is now **live**. You can open it in a browser at `http://localhost:3000`.

**Learning Point**: 
- `npm run dev` is defined in `package.json` as `next dev`. It's a convenience command.
- Next.js dev server includes HMR (hot module replacement): change TypeScript/JSX → browser auto-refreshes. Great for development speed.
- First load compiles React components and Tailwind CSS (~10 seconds). Subsequent loads are faster.
- If you see `Error: Cannot find module 'next'`, run `npm install` again.

---

## PHASE 5: USE THE APPLICATION (10 minutes)

### Step 5.1: Open Frontend in Browser
Navigate to `http://localhost:3000` in your browser.

**Expected View**: Login form with fields:
- Username (default: `admin`)
- Password (default: `changeme123`)
- "Login" button

**Learning Point**: The form is styled with Tailwind CSS (defined in `src/app/LoginForm.tsx`). The UI is responsive and mobile-friendly.

---

### Step 5.2: Login
Enter:
- **Username**: `admin`
- **Password**: `changeme123`
- Click "Login"

**Expected Flow**:
1. Frontend POSTs to `http://localhost:8000/api/login` with credentials
2. Backend validates against demo credentials in `.env`
3. Backend generates JWT token
4. Frontend receives token, stores in `localStorage`
5. Frontend redirects to chat interface

**How to Verify** (Browser Developer Tools):
1. Open Developer Tools (F12 or Cmd+Option+I)
2. Go to "Storage" → "Local Storage" → `http://localhost:3000`
3. Look for key `aiops_token` with a long base64 string as value

**Learning Point**: 
- JWT tokens are **opaque** from the frontend's perspective. The token contains encoded user info (username, issued time, expiration), but the frontend doesn't decode it.
- Tokens are stored in `localStorage`, which persists across browser sessions until manually cleared (or "logout" is clicked).
- **Security note**: In production, use `httpOnly` cookies (not accessible to JavaScript) to prevent XSS theft of tokens.

---

### Step 5.3: Explore Chat Interface
After login, you'll see:
- **Left side**: Sample questions (clickable shortcuts)
- **Center**: Chat area with messages
- **Bottom**: Input field for your question
- **Top right**: Logout button

**Learning Point**: The chat UI is a **stateless component**. Each question is an independent HTTP POST to the backend. The frontend maintains conversation history in React state (`useState`), but it's not persisted server-side.

---

### Step 5.4: Ask Your First Question (Text-to-SQL)
Click or type one of these questions:

**Question 1: Database Count Query**
```
How many critical vulnerabilities are currently open?
```

**Expected Flow**:
1. Frontend POSTs to `/api/agent` with the question
2. Backend agent decides: "This is a database question" → calls `text_to_sql.ask()`
3. `text_to_sql.ask()`:
   - Builds schema description (employees, servers, incidents, vulnerabilities)
   - Prompts Ollama `qwen3:8b`: "Convert to SQL: How many critical vulnerabilities are currently open?"
   - Ollama returns SQL (might include markdown fences or reasoning)
   - SQL validation: checks for forbidden keywords, ensures SELECT statement
   - Executes against `readonly_engine` (aiops_reader role, 5-second timeout, max 200 rows)
   - Ollama generates plain-English explanation
4. Frontend receives response: `{question, tool_used, answer, sql, rows, ...}`
5. Frontend displays results in ResultCard

**Expected Result** (example):
```
Tool Used: query_database
SQL: SELECT COUNT(*) FROM vulnerabilities WHERE severity = 'Critical' AND status = 'open';
Answer: There are currently 12 critical vulnerabilities that are open and require immediate attention.
Rows: [{count: 12}]
```

**Learning Point**: 
- The LLM generates SQL, but SQL generation is **not guaranteed to be correct**. The guardrails prevent **dangerous** SQL (INSERT/UPDATE/DELETE), but the SQL might not answer the question correctly. For example, it might count `severity = 'critical'` (lowercase) when the data has `'Critical'` (titlecase). This is why the result validation step is important.
- The explanation (plain English summary) is the LLM's interpretation of the result rows. For a single row with `{count: 12}`, it might say "there are 12 open critical vulnerabilities" or "12 critical issues are currently active". The exact wording varies per LLM generation.

**Testing Other Text-to-SQL Questions**:
```
Show employees earning more than 15 lakh with 5+ years experience
```
Expected: List of employees with name, salary, years_experience

```
Which team has the most open incidents?
```
Expected: Team name and open incident count

**Learning Point**: Text-to-SQL works best for **structured queries** (counts, filters, aggregations). It works less well for complex analytical questions requiring multiple joins or subqueries.

---

### Step 5.5: Ask a Procedural Question (RAG)
```
What is the procedure for a P1 incident?
```

**Expected Flow**:
1. Frontend POSTs to `/api/agent`
2. Backend agent decides: "This is a procedural question" → calls `rag.answer_from_docs()`
3. `rag.answer_from_docs()`:
   - Embeds the question using Ollama `nomic-embed-text`
   - Queries ChromaDB for top-4 most similar document chunks
   - (Chunks come from `incident_management_sop.md`)
   - Builds context: "Here are 4 document chunks about incident management"
   - Prompts Ollama: "Using only this context, answer: What is the procedure for a P1 incident?"
   - Ollama returns answer + chunk sources
4. Frontend displays answer with source attribution

**Expected Result** (example):
```
Tool Used: search_documents
Answer: For P1 incidents, follow these steps: 1) Declare P1 immediately in the incident tracker, 2) Page on-call manager and engineering lead, 3) Stand up a war room conference bridge, 4) Gather facts and scope for 15 minutes, 5) Begin mitigation immediately without waiting for root cause analysis, 6) Post updates to status page every 15 minutes, 7) Continue until service is restored, 8) Post-incident review within 48 hours.
Sources:
- incident_management_sop.md (chunk 3)
- incident_management_sop.md (chunk 4)
```

**Learning Point**: 
- RAG answers are **grounded** in documents. The LLM must generate answers using only the retrieved chunks. This prevents hallucination (making up info).
- If the documents don't cover a question, the LLM will say "I couldn't find this information in the documents" (learned during training + instruction-tuning).
- Source attribution shows which chunks were used. You can cross-check by opening `backend/docs_corpus/incident_management_sop.md` and searching for keywords.

**Testing Other RAG Questions**:
```
What are the SLA timelines for remediating vulnerabilities?
```
Expected: SLA info from `vulnerability_management_policy.md`

```
Explain the change management process
```
Expected: Change control procedures from `change_management_policy.md`

---

### Step 5.6: Ask a Hybrid Question (Agent Decides)
```
How many employees are in the Engineering department and what is the change management process?
```

**Expected Flow**:
1. Agent sees this is **ambiguous**: could be database + RAG
2. Agent might call **one** tool (simple implementation) or **both** tools (extended implementation)
3. Returns combined response

**Current implementation** (in agent.py): Simple single-step routing. The agent picks ONE tool and returns results from that tool.

**Future enhancement**: Multi-step agent that calls both tools and synthesizes the results.

**Learning Point**: Agents are **composable**. You can extend `run_agent()` to handle multiple tool calls, fallback logic, retry logic, etc., without changing the API contract (still returns `{question, tool_used, answer, ...}`).

---

## PHASE 6: VERIFICATION & TROUBLESHOOTING (5 minutes)

### Step 6.1: Verify Full Stack is Running
Check all three processes:

**1. Backend API:**
```bash
curl http://localhost:8000/health
```
Expected: `{"status":"ok"}`

**2. Frontend Dev Server:**
```bash
curl http://localhost:3000
```
Expected: HTML page (will be large)

**3. Database:**
```bash
psql -U rajas.pr -d aiops -c "SELECT 1;"
```
Expected: `1` (single row)

---

### Step 6.2: Test Token Persistence
1. Login to `http://localhost:3000`
2. Open Developer Tools → Application → Local Storage
3. Verify `aiops_token` key exists with a token value
4. Close the browser tab and reopen `http://localhost:3000`
5. You should be logged in automatically (token loaded from localStorage)

**Learning Point**: This is why tokens are useful: stateless session management. No server-side session storage needed.

---

### Step 6.3: Monitor Backend Logs
In the backend terminal, watch for request logs:

**Example Successful Login**:
```
INFO:     127.0.0.1:54321 - "POST /api/login HTTP/1.1" 200 OK
```

**Example Agent Query**:
```
INFO:     127.0.0.1:54322 - "POST /api/agent HTTP/1.1" 200 OK
```

**Example Error** (will also appear):
```
ERROR:    Unhandled exception
Traceback (most recent call last):
  ...
```

**Learning Point**: Server logs are essential for debugging. If a request returns 500 error, check the backend logs for the full stack trace.

---

### Step 6.4: Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| "Cannot connect to Ollama" | Ollama not running or wrong URL | Run `ollama serve` and verify `http://localhost:11434/api/tags` |
| "Database role 'aiops_reader' does not exist" | Initialization script not run | Run `psql -U postgres -d aiops -f db_init/01_create_reader_role.sql` |
| "Frontend cannot reach backend" | CORS issue or backend not running | Verify backend running with `curl http://localhost:8000/health` |
| "No chunks in ChromaDB" | RAG documents not ingested | Run `python -c "from app.rag import ingest_docs; ingest_docs()"` |
| "Text-to-SQL returns 'Forbidden keyword found'" | Query contains INSERT/UPDATE/DELETE/etc. | This is intentional (security feature). Query is safely rejected. |

---

## PHASE 7: DEEPER LEARNING - EXECUTE & UNDERSTAND EACH MODULE

After the basic flow works, dive deeper into each component:

### Module 1: Text-to-SQL (`backend/app/text_to_sql.py`)

**Execute a Manual Test:**
```bash
cd /Users/rajas.pr/fullstack-ai-assistant/backend
source .venv/bin/activate

python -c "
from app.text_to_sql import ask
from app.db import SessionLocal

db = SessionLocal()
result = ask('How many employees are in Engineering department?', db)
print('Question:', result['question'])
print('SQL:', result['sql'])
print('Result:', result['result'])
print('Explanation:', result['explanation'])
"
```

**Expected Output**:
```
Question: How many employees are in Engineering department?
SQL: SELECT COUNT(*) FROM employees WHERE department = 'Engineering';
Result: {'count': 8}
Explanation: There are currently 8 employees in the Engineering department.
```

**Learning Points**:
1. `ask()` takes a question and SQLAlchemy session
2. Returns dict with `question`, `sql`, `result` (query rows), `explanation`
3. The SQL is generated by LLM (non-deterministic) but validated
4. The explanation is also LLM-generated

**Trace the Execution Flow:**
Open `text_to_sql.py` and follow these functions in order:
```
ask(question, db)
  └─> _call_ollama() with schema + question
  └─> _extract_sql() to parse LLM response
  └─> validate_sql() to check forbidden keywords
  └─> execute_sql() against readonly_engine
  └─> _call_ollama() again to explain result
  └─> return {question, sql, rows, explanation}
```

**Key Security Points**:
1. `validate_sql()` checks `FORBIDDEN_KEYWORDS` regex
2. `execute_sql()` uses `readonly_engine` (limited to `aiops_reader` role)
3. `ReadOnlySessionLocal()` guarantees read-only even if validation fails
4. Row limit: max 200 rows returned

**Experiment**: Try a dangerous query:
```python
result = ask('DROP TABLE employees; --', db)
```
Expected: `UnsafeSQLError: Forbidden keyword found: drop`

---

### Module 2: RAG (`backend/app/rag.py`)

**Execute a Manual Test:**
```bash
python -c "
from app.rag import answer_from_docs

result = answer_from_docs('What is a P1 incident?')
print('Answer:', result['answer'])
print('Sources:', result['sources'])
"
```

**Expected Output**:
```
Answer: A P1 incident is the most critical severity level for operational incidents. It indicates a complete service outage or severe degradation affecting all or most customers. P1 incidents require immediate response and escalation to senior engineering leadership. The goal is to restore service as quickly as possible, with status updates provided every 15 minutes.
Sources: [{'source': 'incident_management_sop.md', 'chunk_index': 2}, ...]
```

**Learning Points**:
1. `answer_from_docs()` takes a question (string), no session needed
2. Returns `{answer, sources}` where sources show which chunks were retrieved
3. The answer is **grounded** in the retrieved chunks

**Trace the Execution Flow:**
```
answer_from_docs(question)
  └─> _embed(question) using Ollama nomic-embed-text
  └─> _get_collection() from ChromaDB
  └─> collection.query() for top-4 similar chunks
  └─> Build context from retrieved chunks
  └─> _call_ollama() with context + question
  └─> return {answer, sources}
```

**Experiment: Add a New Document**
1. Create `backend/docs_corpus/my_policy.md` with content:
   ```markdown
   # My Custom Policy

   All employees must follow this policy.
   ```
2. Run ingestion:
   ```bash
   python -c "from app.rag import ingest_docs; print(ingest_docs())"
   ```
3. Query:
   ```bash
   python -c "from app.rag import answer_from_docs; print(answer_from_docs('What is the custom policy?')['answer'])"
   ```

**Learning Points**:
- ChromaDB ingestion is **one-shot**: documents are chunked, embedded, and stored
- Subsequent queries only retrieve; no re-ingestion needed
- If you edit a document, you must re-run `ingest_docs()`
- Embedding takes time (~1 sec per chunk). For 100 documents, plan 5-10 minutes

---

### Module 3: Agent Routing (`backend/app/agent.py`)

**Execute a Manual Test:**
```bash
python -c "
from app.agent import run_agent
from app.db import SessionLocal

db = SessionLocal()

# Question 1: Database question
result = run_agent('How many employees are in Engineering?', db)
print('Tool Used:', result['tool_used'])
print('Answer:', result['answer'][:100], '...')
print()

# Question 2: Procedural question
result = run_agent('What is the P1 incident process?', db)
print('Tool Used:', result['tool_used'])
print('Answer:', result['answer'][:100], '...')
"
```

**Expected Output**:
```
Tool Used: query_database
Answer: There are 8 employees in the Engineering department. ...

Tool Used: search_documents
Answer: P1 incidents are the highest priority level and require immediate response. ...
```

**Learning Points**:
1. `run_agent()` uses Ollama's native tool-calling to decide which tool to invoke
2. Tool decision is made by the LLM: it sees tool descriptions and picks the best one
3. Current implementation: single-step (one tool call per question)

**Trace the Execution Flow:**
```
run_agent(question, db)
  └─> _decide_tool(question)
      └─> Ollama /api/chat with tools parameter
      └─> LLM generates tool_calls response
      └─> Extract tool name from response
  └─> if tool == "query_database": text_to_sql.ask()
  └─> if tool == "search_documents": rag.answer_from_docs()
  └─> return {question, tool_used, ...result from chosen tool}
```

**Tool Definition** (in agent.py):
```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_database",
            "description": "Answer questions about employees, servers, incidents, and vulnerabilities...",
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
            "description": "Answer questions about company policies, SOPs...",
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
            },
        },
    },
]
```

**Experiment: Add a Third Tool**
1. Create a new tool in `agent.py`: `{name: "search_employees_by_salary", ...}`
2. Add logic in `run_agent()` to handle this tool
3. Now the agent can decide: database questions, docs questions, or salary filter questions

---

### Module 4: Models & Database (`backend/app/models.py`)

**Inspect the Schema:**
```bash
python -c "
from app.models import Employee, Server, Incident, Vulnerability
from sqlalchemy import inspect

for model in [Employee, Server, Incident, Vulnerability]:
    mapper = inspect(model)
    print(f'{model.__name__}:')
    for col in mapper.columns:
        print(f'  {col.name}: {col.type}')
    print()
"
```

**Expected Output**:
```
Employee:
  id: INTEGER
  name: VARCHAR
  department: VARCHAR
  role: VARCHAR
  hire_date: DATE
  salary: NUMERIC
  years_experience: INTEGER

Server:
  id: INTEGER
  hostname: VARCHAR
  environment: VARCHAR
  os: VARCHAR
  team: VARCHAR

...
```

**Learning Points**:
1. SQLAlchemy models are Python classes that map to database tables
2. Each class attribute is a column
3. `relationship()` defines foreign key relationships (e.g., Server.vulnerabilities returns all related Vulnerability objects)
4. This is the **source of truth** for schema. The database is created from these models.

---

### Module 5: Authentication (`backend/app/auth.py`)

**Execute a Manual Test:**
```bash
python -c "
from app.auth import authenticate, create_access_token, decode_token

# Test login
is_valid = authenticate('admin', 'changeme123')
print('Login valid:', is_valid)

# Test token generation
token = create_access_token('admin')
print('Token:', token[:50], '...')

# Test token decoding
username = decode_token(token)
print('Username from token:', username)
"
```

**Expected Output**:
```
Login valid: True
Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... 
Username from token: admin
```

**Learning Points**:
1. Credentials are hardcoded (demo only): check `.env` for DEMO_USERNAME, DEMO_PASSWORD
2. Tokens are JWT (JSON Web Tokens): base64-encoded JSON with signature
3. Token contains: `{"username": "admin", "iat": 1700000000, "exp": 1700086400}`
4. `decode_token()` verifies the signature matches the JWT_SECRET

**Security Notes**:
- Passwords are stored in plaintext in `.env` (development only!)
- In production, use bcrypt/scrypt to hash passwords
- JWT_SECRET must be **random and long** (e.g., 64+ characters)
- Current setup has no token expiration in the code (should be added)

---

### Module 6: Frontend Components (`frontend/src/app/`)

**Inspect Key Components:**

**page.tsx** - Main chat interface:
```bash
cat /Users/rajas.pr/fullstack-ai-assistant/frontend/src/app/page.tsx | head -80
```

**Key Functions**:
- `useEffect()` on mount: load token from localStorage
- `ask()`: POST to `/api/agent` with the question
- `handleLogin()`: store token, update state
- `handleLogout()`: clear token, clear chat history

**Learning Points**:
1. React hooks (`useState`, `useEffect`) manage component state
2. API calls use `fetch()` API (native to browsers)
3. Authorization header: `Authorization: Bearer ${token}`
4. Errors: if response is 401, logout the user

**LoginForm.tsx** - Authentication:
```bash
cat /Users/rajas.pr/fullstack-ai-assistant/frontend/src/app/LoginForm.tsx | head -50
```

**Key Functions**:
- Form submission: `handleLogin()`
- POST to `/api/login` with username/password
- Parent receives `onLoginSuccess(token)` callback

**ResultCard.tsx** - Result display:
```bash
cat /Users/rajas.pr/fullstack-ai-assistant/frontend/src/app/ResultCard.tsx | head -80
```

**Key Functions**:
- Accepts `entry` (chat entry from API)
- Renders different UI based on `tool_used`:
  - Database: show SQL, rows in table format
  - Documents: show sources with links
  - Error: show error message

---

### Module 7: Database Connections (`backend/app/db.py`)

**Understand Connection Pooling:**
```bash
python -c "
from app.db import engine, readonly_engine

print('Main engine URL:', engine.url)
print('Main engine pool:', engine.pool)
print('Readonly engine URL:', readonly_engine.url)
print('Readonly engine pool:', readonly_engine.pool)
"
```

**Output**:
```
Main engine URL: postgresql+psycopg2://rajas.pr@localhost:5432/aiops
Main engine pool: <sqlalchemy.pool.QueuePool object at 0x...>
Readonly engine URL: postgresql+psycopg2://aiops_reader:readonly_dev_pw@localhost:5432/aiops
Readonly engine pool: <sqlalchemy.pool.QueuePool object at 0x...>
```

**Learning Points**:
1. **Two engines**: one for app (full privileges), one for LLM (read-only)
2. **Connection pooling**: engines maintain a pool of DB connections (improves performance)
3. `pool_pre_ping=True`: pings connections before using (checks they're still alive)
4. Dependency injection: `@app.get("/path", dependencies=[Depends(get_db)])` provides session to route

---

## PHASE 8: RUN TESTS

### Step 8.1: Run All Tests
```bash
cd /Users/rajas.pr/fullstack-ai-assistant/backend
source .venv/bin/activate

pytest -v
```

**Expected Output**:
```
test_api.py::test_health PASSED
test_api.py::test_login_success PASSED
test_api.py::test_login_failure PASSED
test_auth.py::test_create_token PASSED
test_auth.py::test_decode_token PASSED
test_text_to_sql_guardrails.py::test_forbidden_keyword_insert PASSED
test_text_to_sql_guardrails.py::test_forbidden_keyword_delete PASSED
...

====== 15 passed in 3.45s ======
```

**Learning Points**:
1. Tests verify core functionality doesn't break
2. `test_text_to_sql_guardrails.py` is particularly important: ensures dangerous SQL is caught
3. Run tests **before** deploying any changes
4. Add new tests when adding features

---

## PHASE 9: PRODUCTION CHECKLIST

After understanding the system, here's what's needed for production:

| Item | Current | Production |
|------|---------|-----------|
| **Secrets** | Hardcoded in .env | Use environment variables, secrets manager (AWS Secrets, Vault, etc.) |
| **Database Passwords** | Dev credentials visible | Rotate to strong passwords, use IAM roles |
| **JWT Secret** | Visible in code | Random 64-char string from secrets manager |
| **Ollama** | Local on host | Deploy Ollama server to separate machine or container |
| **Frontend CORS** | Hardcoded localhost | Use environment-based config |
| **Logging** | JSON to stdout | Forward to centralized logging (ELK, Splunk, CloudWatch) |
| **Error Handling** | Generic "Internal server error" | Detailed error tracking (Sentry, DataDog) |
| **Token Expiration** | No expiration in code | Add expiration checks, refresh token logic |
| **Session Storage** | localStorage | Use httpOnly cookies |
| **Database Backups** | Manual | Automated daily backups |
| **Monitoring** | None | Health checks, error rates, latency metrics |
| **Rate Limiting** | None | Add rate limiting per user/IP |
| **API Versioning** | None | Add `/api/v1/` prefix for future compatibility |

---

## Summary Table: Execution Order & Learning

| Phase | Command(s) | Learning Point | Time |
|-------|-----------|---|------|
| 1.1 | `python3.14 --version` | Verify Python installation | 1 min |
| 1.2 | `node --version` | Verify Node.js | 1 min |
| 1.3 | `brew services list\|grep postgres` | Database must run | 1 min |
| 1.4 | `curl http://localhost:11434/api/tags` | Ollama must have models | 1 min |
| 2.1-2.2 | `python3.14 -m venv .venv` | Virtual environments isolate dependencies | 2 min |
| 2.3 | `source .venv/bin/activate` | Activation modifies PATH | <1 min |
| 2.4 | `pip install -r requirements.txt` | Dependencies pinned for reproducibility | 5 min |
| 2.6 | `psql -U postgres -d aiops -f db_init/01_create_reader_role.sql` | Read-only role is security boundary | 1 min |
| 2.7 | `python -m app.seed` | Sample data for testing | 2 min |
| 2.8 | `python -c "from app.rag import ingest_docs; ingest_docs()"` | RAG requires embedded documents | 3 min |
| 3.1 | `uvicorn app.main:app --port 8000 --reload` | Backend API lives here | 2 min |
| 4.2 | `npm install` | Node.js dependencies | 3 min |
| 4.3 | `npm run dev` | Frontend dev server with HMR | 2 min |
| 5.2-5.6 | Browser interaction | Test full pipeline | 5 min |
| 7.1 | `pytest -v` | Verify guardrails work | 3 min |

---

## Final Learning Points

### Architecture
- **Frontend** makes HTTP requests → **Backend** routes to Text-to-SQL or RAG → **Database** or **Vector Store** returns data → **Ollama** generates response
- **Security**: Defense-in-depth with role-based access, SQL validation, statement timeout, row limits

### Execution Order Matters
- Prerequisites (Python, Node, Postgres, Ollama) must be verified **first**
- Backend setup (venv, dependencies, DB init, seed, RAG ingest) **before** starting server
- Keep backend running while developing frontend
- Always verify connectivity with simple tests (`curl`, `psql`) before assuming something works

### Local Development Best Practices
- Use virtual environments (Python) and `node_modules` (Node) to isolate dependencies
- Run dev servers with auto-reload (`--reload`, HMR) for fast iteration
- Use `.env` files for local secrets (but never commit to git)
- Monitor server logs (stdout) for errors and request traces

### This System is Production-Grade
- Full authentication (JWT), authorization (roles), and encryption (TLS potential)
- Structured logging (JSON)
- Error handling with consistent responses
- Test coverage (API, auth, guardrails)
- Modular architecture (easy to extend)

Ready to explore further? Start with reading [REVERSE_ENGINEERING.md](REVERSE_ENGINEERING.md) for deeper technical details, or check [frontend/README.md](frontend/README.md) for frontend-specific knowledge.
