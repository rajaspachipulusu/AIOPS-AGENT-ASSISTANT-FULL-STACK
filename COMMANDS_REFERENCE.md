# QUICK EXECUTION REFERENCE - Commands in Order

Copy and paste these commands in sequence. Each section is one phase.

---

## PHASE 1: VERIFY PREREQUISITES (5 min)

```bash
# 1.1 - Verify Python 3.14
/opt/homebrew/bin/python3.14 --version

# 1.2 - Verify Node.js
/opt/homebrew/bin/node --version

# 1.3 - Verify PostgreSQL Running
brew services list | grep postgres
# If not running: brew services start postgresql@16
psql -U postgres -c "SELECT version();"

# 1.4 - Verify Ollama + Models
curl http://localhost:11434/api/tags
# If Ollama not running: ollama serve
# If models missing: ollama pull qwen3:8b && ollama pull nomic-embed-text
```

---

## PHASE 2: BACKEND SETUP (20 min)

```bash
# 2.1 - Navigate to backend
cd /Users/rajas.pr/fullstack-ai-assistant/backend

# 2.2 - Create virtual environment
/opt/homebrew/bin/python3.14 -m venv .venv

# 2.3 - Activate venv
source .venv/bin/activate

# 2.4 - Install dependencies
pip install -r requirements.txt

# 2.5 - Verify installation
python -c "import sqlalchemy, fastapi, pydantic; print('✓ Core packages installed')"

# 2.6 - Create database role (FIRST TIME ONLY)
psql -U postgres -d aiops -f db_init/01_create_reader_role.sql

# 2.7 - Seed sample data
python -m app.seed

# 2.8 - Ingest RAG documents
python -c "from app.rag import ingest_docs; chunks = ingest_docs(); print(f'✓ Ingested {chunks} chunks')"
```

---

## PHASE 3: START BACKEND API (Keep Running)

```bash
# 3.1 - Start Uvicorn server (DO NOT STOP - keep this terminal running)
uvicorn app.main:app --port 8000 --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

---

## PHASE 4: FRONTEND SETUP (In New Terminal Tab)

```bash
# 4.1 - Navigate to frontend
cd /Users/rajas.pr/fullstack-ai-assistant/frontend

# 4.2 - Install dependencies
/opt/homebrew/bin/npm install

# 4.3 - Start dev server (DO NOT STOP - keep running)
/opt/homebrew/bin/npm run dev
```

**Expected output:**
```
▲ Next.js 16.3.8
- Local: http://localhost:3000
```

---

## PHASE 5: USE THE APPLICATION

```
1. Open browser: http://localhost:3000
2. Login: admin / changeme123
3. Ask a question:
   - Database: "How many critical vulnerabilities are open?"
   - Documents: "What is the P1 incident process?"
4. View results
```

---

## PHASE 6: DEEPER TESTING (In Backend Terminal)

```bash
# 6.1 - Test Text-to-SQL manually
python -c "
from app.text_to_sql import ask
from app.db import SessionLocal

db = SessionLocal()
result = ask('How many employees are in Engineering?', db)
print('SQL:', result['sql'])
print('Explanation:', result['explanation'])
"

# 6.2 - Test RAG manually
python -c "
from app.rag import answer_from_docs

result = answer_from_docs('What is a P1 incident?')
print('Answer:', result['answer'][:200])
"

# 6.3 - Test Agent Routing
python -c "
from app.agent import run_agent
from app.db import SessionLocal

db = SessionLocal()
result = run_agent('How many employees earn more than 1 million?', db)
print('Tool Used:', result['tool_used'])
print('Answer:', result['answer'][:200])
"

# 6.4 - Run all tests
pytest -v
```

---

## PHASE 7: VERIFICATION CHECKLIST

```bash
# Verify backend
curl http://localhost:8000/health

# Verify database
psql -U rajas.pr -d aiops -c "SELECT COUNT(*) FROM employees;"

# Verify token persists
# (Open browser dev tools → Storage → Local Storage → check aiops_token)
```

---

## Key Commands by Module

### Text-to-SQL Pipeline
```bash
# See SQL generation in action
python -c "
from app.text_to_sql import ask
from app.db import SessionLocal

db = SessionLocal()

# Test various questions
questions = [
    'How many P1 incidents are open?',
    'Show employees earning more than 15 lakh',
    'Which team has the most vulnerabilities?'
]

for q in questions:
    result = ask(q, db)
    print(f'Q: {q}')
    print(f'SQL: {result[\"sql\"]}')
    print()
"
```

### RAG Retrieval
```bash
# See document retrieval in action
python -c "
from app.rag import answer_from_docs

questions = [
    'What is the incident response procedure?',
    'What are the vulnerability SLAs?',
    'Explain the change management process'
]

for q in questions:
    result = answer_from_docs(q)
    print(f'Q: {q}')
    print(f'Sources: {[s[\"source\"] for s in result[\"sources\"]]}')
    print(f'Answer: {result[\"answer\"][:150]}...')
    print()
"
```

### Agent Routing
```bash
# See agent decide between SQL and RAG
python -c "
from app.agent import run_agent
from app.db import SessionLocal

db = SessionLocal()

test_cases = [
    ('How many open critical vulnerabilities?', 'database'),
    ('What is the P1 incident procedure?', 'documents'),
    ('Which server has the most vulnerabilities?', 'database'),
    ('What is the change management SLA?', 'documents'),
]

for question, expected_tool in test_cases:
    result = run_agent(question, db)
    status = '✓' if result['tool_used'].replace('_', ' ') in expected_tool else '✗'
    print(f'{status} Q: {question}')
    print(f'  Tool: {result[\"tool_used\"]}')
"
```

### Database Introspection
```bash
# See what's in the database
psql -U rajas.pr -d aiops -c "
SELECT
  'Employees' AS entity, COUNT(*) AS count FROM employees
UNION ALL
SELECT 'Servers', COUNT(*) FROM servers
UNION ALL
SELECT 'Incidents', COUNT(*) FROM incidents
UNION ALL
SELECT 'Vulnerabilities', COUNT(*) FROM vulnerabilities;
"

# See specific data
psql -U rajas.pr -d aiops -c "SELECT name, department, salary FROM employees LIMIT 5;"
```

### Authentication Testing
```bash
# Test token generation and validation
python -c "
from app.auth import authenticate, create_access_token, decode_token

# Test wrong credentials
print('Wrong password:', authenticate('admin', 'wrong'))

# Test correct credentials
print('Correct login:', authenticate('admin', 'changeme123'))

# Test token flow
token = create_access_token('admin')
decoded_username = decode_token(token)
print('Token roundtrip:', decoded_username)
"
```

---

## Environment Variables Reference

**File**: `backend/.env`

```
DATABASE_URL=postgresql+psycopg2://rajas.pr@localhost:5432/aiops
READONLY_DATABASE_URL=postgresql+psycopg2://aiops_reader:readonly_dev_pw@localhost:5432/aiops
APP_ENV=development
JWT_SECRET=dev-only-insecure-secret-change-me
DEMO_USERNAME=admin
DEMO_PASSWORD=changeme123
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Troubleshooting Commands

```bash
# If backend won't start
# 1. Check syntax errors
python -m py_compile app/main.py app/text_to_sql.py app/rag.py app/agent.py

# 2. Check database connection
psql -U rajas.pr -d aiops -c "SELECT 1;"

# 3. Check Ollama
curl -I http://localhost:11434/api/tags

# If frontend won't start
# 1. Clear cache
rm -rf frontend/.next node_modules package-lock.json
cd frontend && npm install && npm run dev

# If database is corrupted
# 1. Re-seed
cd backend && python -m app.seed

# 2. Re-ingest RAG docs
cd backend && python -c "from app.rag import ingest_docs; ingest_docs()"

# If venv is broken
# 1. Delete and recreate
rm -rf backend/.venv
cd backend && /opt/homebrew/bin/python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Performance Monitoring

```bash
# Monitor backend requests
# (Watch the Uvicorn terminal - you'll see each request logged)

# Monitor database performance
# (In psql)
SELECT pid, query, query_start FROM pg_stat_activity;

# Monitor Ollama
# (Check CPU/memory while running queries)
ps aux | grep ollama

# Frontend performance
# (Browser dev tools → Network tab → see response times)
```

---

## Clean Reset (If Needed)

```bash
# Complete reset to fresh state
# WARNING: Deletes all data and caches

# Backend
cd backend
rm -rf .venv chroma_store/
source .venv/bin/activate  # Or create new venv first
python -m app.seed
python -c "from app.rag import ingest_docs; ingest_docs()"

# Frontend
cd ../frontend
rm -rf .next node_modules package-lock.json
npm install

# Restart both servers
```

---

## One-Liner Startup (After First Setup)

```bash
# Terminal 1 - Backend
cd /Users/rajas.pr/fullstack-ai-assistant/backend && \
source .venv/bin/activate && \
uvicorn app.main:app --port 8000 --reload

# Terminal 2 - Frontend
cd /Users/rajas.pr/fullstack-ai-assistant/frontend && \
npm run dev

# Then open http://localhost:3000 in browser
```

---

## API Testing with curl

```bash
# Health check
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/health/db

# Login
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"changeme123"}' | jq .

# Agent query (with token)
TOKEN=$(curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"changeme123"}' | jq -r .access_token)

curl -X POST http://localhost:8000/api/agent \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question":"How many employees are in Engineering?"}' | jq .
```

---

## Learning Order Recommendation

1. **Get it running** (Phases 1-5): Full end-to-end flow
2. **Verify components** (Phase 6): Test each module independently
3. **Deep dive** (EXECUTION_FLOW.md Phase 7): Understand details
4. **Customize** (add features, modify docs, extend agent)
5. **Deploy** (Production checklist section in EXECUTION_FLOW.md)

---

**Pro Tip**: Keep this file open while working. Ctrl+F to search for the command you need.
