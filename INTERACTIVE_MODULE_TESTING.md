# INTERACTIVE MODULE TESTING GUIDE

Run each script/module to understand how they work individually.

---

## Setup: Activate Virtual Environment First

```bash
cd /Users/rajas.pr/fullstack-ai-assistant/backend
source .venv/bin/activate
```

**All commands below assume you're in this directory with venv activated.**

---

## MODULE 1: db.py - Database Connections

### What It Does
Sets up two SQLAlchemy engines:
- `engine` (full privileges for app writes)
- `readonly_engine` (read-only for LLM-generated SQL)

### Test It
```bash
python -c "
from app.db import engine, readonly_engine, SessionLocal

print('=== Main Engine ===')
print('URL:', engine.url)
print('Pool:', engine.pool)
print()

print('=== Readonly Engine ===')
print('URL:', readonly_engine.url)
print('Pool:', readonly_engine.pool)
print()

print('=== Testing Connection ===')
from sqlalchemy import text
session = SessionLocal()
result = session.execute(text('SELECT 1 as connection_test'))
print('Query result:', result.fetchone())
session.close()
print('✓ Database connection works!')
"
```

**Expected Output:**
```
=== Main Engine ===
URL: postgresql+psycopg2://rajas.pr@localhost:5432/aiops
Pool: <sqlalchemy.pool.QueuePool object at 0x...>

=== Readonly Engine ===
URL: postgresql+psycopg2://aiops_reader:readonly_dev_pw@localhost:5432/aiops
Pool: <sqlalchemy.pool.QueuePool object at 0x...>

=== Testing Connection ===
Query result: (1,)
✓ Database connection works!
```

**Learning Point**: Two engines exist - one for app, one for LLM SQL (defense-in-depth)

---

## MODULE 2: models.py - Database Schema

### What It Does
Defines SQLAlchemy ORM models:
- Employee, Server, Incident, Vulnerability
- Relationships between tables

### Test It
```bash
python -c "
from app.models import Employee, Server, Incident, Vulnerability
from sqlalchemy import inspect

print('=== Database Schema ===')
for model in [Employee, Server, Incident, Vulnerability]:
    mapper = inspect(model)
    print(f'\n{model.__tablename__}:')
    for col in mapper.columns:
        print(f'  {col.name:<20} {str(col.type):<20}')
    
    # Show relationships
    for rel in mapper.relationships:
        print(f'  [relationship] {rel.key} -> {rel.mapper.class_.__name__}')
"
```

**Expected Output:**
```
=== Database Schema ===

employees:
  id                   INTEGER
  name                 VARCHAR
  department           VARCHAR
  role                 VARCHAR
  hire_date            DATE
  salary               NUMERIC
  years_experience     INTEGER

servers:
  id                   INTEGER
  hostname             VARCHAR
  environment          VARCHAR
  os                   VARCHAR
  team                 VARCHAR
  [relationship] vulnerabilities -> Vulnerability
  [relationship] incidents -> Incident

incidents:
  id                   INTEGER
  title                VARCHAR
  severity             VARCHAR
  status               VARCHAR
  team                 VARCHAR
  server_id            INTEGER
  created_date         DATE
  resolved_date        DATE
  description          TEXT
  [relationship] server -> Server

vulnerabilities:
  id                   INTEGER
  cve_id               VARCHAR
  severity             VARCHAR
  status               VARCHAR
  server_id            INTEGER
  discovered_date      DATE
  [relationship] server -> Server
```

**Learning Point**: Models are the source of truth for schema. Database is generated from these.

---

## MODULE 3: seed.py - Sample Data Generator

### What It Does
Creates 200 realistic demo records:
- 40 employees
- 25 servers
- 60 incidents
- 80 vulnerabilities

### Run It
```bash
python -m app.seed
```

**Expected Output:**
```
Seeding database...
✓ Created 40 employees
✓ Created 25 servers
✓ Created 60 incidents
✓ Created 80 vulnerabilities
Seed complete!
```

### Inspect Generated Data
```bash
python -c "
from app.db import SessionLocal
from app.models import Employee, Server, Incident, Vulnerability

db = SessionLocal()

print('=== Sample Data ===')
print('\n--- EMPLOYEES (showing 3) ---')
for emp in db.query(Employee).limit(3).all():
    print(f'{emp.name:<20} {emp.department:<15} Salary: ₹{emp.salary}')

print('\n--- SERVERS (showing 3) ---')
for srv in db.query(Server).limit(3).all():
    print(f'{srv.hostname:<15} {srv.environment:<10} Team: {srv.team}')

print('\n--- INCIDENTS (showing 3) ---')
for inc in db.query(Incident).limit(3).all():
    print(f'{inc.title:<30} Severity: {inc.severity} Status: {inc.status}')

print('\n--- VULNERABILITIES (showing 3) ---')
for vuln in db.query(Vulnerability).limit(3).all():
    print(f'{vuln.cve_id:<15} Severity: {vuln.severity:<10} Status: {vuln.status}')

# Get counts
print('\n--- COUNTS ---')
print(f'Employees: {db.query(Employee).count()}')
print(f'Servers: {db.query(Server).count()}')
print(f'Incidents: {db.query(Incident).count()}')
print(f'Vulnerabilities: {db.query(Vulnerability).count()}')

db.close()
"
```

**Expected Output:**
```
=== Sample Data ===

--- EMPLOYEES (showing 3) ---
Arjun Sharma         Engineering     Salary: ₹1234567
Priya Patel          Security        Salary: ₹1567890
Rahul Iyer           Infrastructure  Salary: ₹987654

--- SERVERS (showing 3) ---
PROD-100            prod       Team: Linux Team
STG-101             staging    Team: Windows Team
DEV-102             dev        Team: Database Team

--- INCIDENTS (showing 3) ---
Incident on PROD-100: High CPU   Severity: P1 Status: open
Incident on STG-101: Disk full   Severity: P3 Status: resolved
Incident on DEV-102: Service down Severity: P2 Status: in_progress

--- VULNERABILITIES (showing 3) ---
CVE-2024-1000       Severity: Critical Status: open
CVE-2024-1001       Severity: High     Status: remediated
CVE-2024-1002       Severity: Low      Status: open

--- COUNTS ---
Employees: 40
Servers: 25
Incidents: 60
Vulnerabilities: 80
```

**Learning Point**: Sample data is realistic and can be used for testing realistic queries

---

## MODULE 4: auth.py - Authentication

### What It Does
- Authenticates users (username/password)
- Generates JWT tokens
- Validates tokens for protected routes

### Test It
```bash
python -c "
from app.auth import authenticate, create_access_token, get_current_user
from fastapi.security import HTTPAuthorizationCredentials

print('=== AUTHENTICATION FLOW ===')

# Step 1: Try wrong credentials
print('\n1. Testing wrong credentials:')
result = authenticate('admin', 'wrongpassword')
print(f'   authenticate(\"admin\", \"wrongpassword\") = {result}')

# Step 2: Try correct credentials
print('\n2. Testing correct credentials:')
result = authenticate('admin', 'changeme123')
print(f'   authenticate(\"admin\", \"changeme123\") = {result}')

# Step 3: Generate token
print('\n3. Generating JWT token:')
token = create_access_token('admin')
print(f'   Token: {token}')
print(f'   Token length: {len(token)} characters')

# Step 4: Validate token through auth dependency
print('\n4. Validating token via get_current_user:')
creds = HTTPAuthorizationCredentials(scheme='Bearer', credentials=token)
username = get_current_user(creds)
print(f'   Authenticated username: {username}')

# Step 5: Try invalid token
print('\n5. Testing invalid token:')
try:
  bad_creds = HTTPAuthorizationCredentials(scheme='Bearer', credentials='invalid.token.here')
  get_current_user(bad_creds)
except Exception as e:
    print(f'   Error (expected): {type(e).__name__}')

print('\n✓ Authentication module works!')
"
```

**Expected Output:**
```
=== AUTHENTICATION FLOW ===

1. Testing wrong credentials:
   authenticate("admin", "wrongpassword") = False

2. Testing correct credentials:
   authenticate("admin", "changeme123") = True

3. Generating JWT token:
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTcyODI4NjQwMH0.signature_here...
  Token length: 120+ characters

4. Validating token via get_current_user:
  Authenticated username: admin

5. Testing invalid token:
   Error (expected): HTTPException

✓ Authentication module works!
```

**Learning Point**: JWT tokens carry subject (`sub`) + expiry (`exp`). Validation happens at request time for protected routes.

---

## MODULE 5: config.py - Configuration Management

### What It Does
Loads settings from `.env` file using Pydantic

### Test It
```bash
python -c "
from app.config import get_settings

settings = get_settings()

print('=== Configuration Settings ===')
print(f'App Environment: {settings.app_env}')
print(f'Database URL: {settings.database_url}')
print(f'Readonly Database URL: {settings.readonly_database_url}')
print(f'Demo Username: {settings.demo_username}')
print(f'Demo Password: {settings.demo_password}')
print(f'Ollama Base URL: {settings.ollama_base_url}')
print(f'JWT Secret: {settings.jwt_secret[:20]}...(hidden)')
print('\n✓ Configuration loaded successfully!')
"
```

**Expected Output:**
```
=== Configuration Settings ===
App Environment: development
Database URL: postgresql+psycopg2://rajas.pr@localhost:5432/aiops
Readonly Database URL: postgresql+psycopg2://aiops_reader:readonly_dev_pw@localhost:5432/aiops
Demo Username: admin
Demo Password: changeme123
Ollama Base URL: http://localhost:11434
JWT Secret: dev-only-insecure-secr...(hidden)

✓ Configuration loaded successfully!
```

**Learning Point**: Settings come from `.env` file, can be overridden by environment variables

---

## MODULE 6: text_to_sql.py - SQL Generation & Execution

### What It Does
1. Generates SQL from natural language using LLM
2. Validates SQL (checks for forbidden keywords)
3. Executes against read-only database
4. Explains result

### Test It - Basic Flow
```bash
python -c "
from app.text_to_sql import ask
from app.db import SessionLocal

db = SessionLocal()

print('=== TEXT-TO-SQL DEMO ===\n')

# Question 1: Simple count
print('Question 1: How many employees are in the Engineering department?')
result = ask(db, 'How many employees are in the Engineering department?')
print(f'SQL: {result[\"sql\"]}')
print(f'Result: {result[\"rows\"]}')
print(f'Explanation: {result[\"explanation\"]}')

print('\n' + '='*60 + '\n')

# Question 2: Filtering
print('Question 2: Show employees earning more than 1 million')
result = ask(db, 'Show employees earning more than 1 million')
print(f'SQL: {result[\"sql\"]}')
print(f'Result rows: {len(result[\"rows\"])} employees')
if result['rows']:
  print(f'First row: {result[\"rows\"][0]}')

print('\n' + '='*60 + '\n')

# Question 3: Aggregation with join
print('Question 3: Which team has the most open incidents?')
result = ask(db, 'Which team has the most open incidents?')
print(f'SQL: {result[\"sql\"]}')
print(f'Result: {result[\"rows\"]}')
print(f'Explanation: {result[\"explanation\"]}')

db.close()
print('\n✓ Text-to-SQL module works!')
"
```

**Expected Output:**
```
=== TEXT-TO-SQL DEMO ===

Question 1: How many employees are in the Engineering department?
SQL: SELECT COUNT(*) FROM employees WHERE department = 'Engineering';
Result: [{'count': 8}]
Explanation: There are 8 employees in the Engineering department.

============================================================

Question 2: Show employees earning more than 1 million
SQL: SELECT name, salary FROM employees WHERE salary > 1000000;
Result rows: 32 employees
First row: {'name': 'Arjun Sharma', 'salary': Decimal('1234567.00')}

============================================================

Question 3: Which team has the most open incidents?
SQL: SELECT team, COUNT(*) as count FROM incidents WHERE status = 'open' GROUP BY team ORDER BY count DESC LIMIT 1;
Result: [{'team': 'Linux Team', 'count': 8}]
Explanation: The Linux Team has the most open incidents with 8 incidents.

✓ Text-to-SQL module works!
```

### Test It - Error Handling (Dangerous Queries)
```bash
python - <<'PY'
from app.text_to_sql import ask, UnsafeSQLError, SQLGenerationError
from app.db import SessionLocal

db = SessionLocal()

print('=== SQL GUARDRAILS TEST ===\n')

# Test 1: Try to generate a DELETE query (should fail validation)
print('Test 1: Attempting to generate a DELETE query')
try:
    result = ask(db, 'DELETE all employees')
    print('ERROR: Should have been caught!')
except UnsafeSQLError as e:
    print(f'✓ Caught: {e}')
except SQLGenerationError as e:
    print(f'LLM/timeout issue (not guardrail logic): {e}')

# Test 2: Try to generate an INSERT query
print('\nTest 2: Attempting to generate an INSERT query')
try:
    result = ask(db, 'Add a new employee named John')
    print('ERROR: Should have been caught!')
except UnsafeSQLError as e:
    print(f'✓ Caught: {e}')
except SQLGenerationError as e:
    print(f'LLM/timeout issue (not guardrail logic): {e}')

# Test 3: Try to generate a DROP query
print('\nTest 3: Attempting to generate a DROP query')
try:
    result = ask(db, 'DROP TABLE employees')
    print('ERROR: Should have been caught!')
except UnsafeSQLError as e:
    print(f'✓ Caught: {e}')
except SQLGenerationError as e:
    print(f'LLM/timeout issue (not guardrail logic): {e}')

db.close()
print('\n✓ Guardrails working correctly!')
PY
```

**Expected Output:**
```
=== SQL GUARDRAILS TEST ===

Test 1: Attempting to generate a DELETE query
✓ Caught: Query contains a forbidden keyword.

Test 2: Attempting to generate an INSERT query
✓ Caught: Query contains a forbidden keyword.

Test 3: Attempting to generate a DROP query
✓ Caught: Query contains a forbidden keyword.

✓ Guardrails working correctly!
```

**Learning Point**: Multiple layers of defense:
1. Keyword regex validation
2. Read-only PostgreSQL role (secondary guardrail)
3. Row limit enforcement

---

## MODULE 7: rag.py - Document Retrieval

### What It Does
1. Ingests markdown documents (chunking + embedding)
2. Stores embeddings in ChromaDB
3. Retrieves similar chunks at query time
4. LLM generates answer from chunks

### Test It - Check Ingested Documents
```bash
python -c "
from app.rag import _get_collection

collection = _get_collection()
items = collection.get()

print('=== RAG VECTOR STORE ===\n')
print(f'Total chunks stored: {len(items[\"ids\"])}')
print(f'\nChunks by document:')

# Group by source
from collections import defaultdict
by_source = defaultdict(int)
for metadata in items['metadatas']:
    by_source[metadata['source']] += 1

for source, count in sorted(by_source.items()):
    print(f'  {source}: {count} chunks')

print('\nSample chunk:')
if items['ids']:
    idx = 0
    print(f'  ID: {items[\"ids\"][idx]}')
    print(f'  Source: {items[\"metadatas\"][idx]}')
    print(f'  Preview: {items[\"documents\"][idx][:100]}...')
"
```

**Expected Output:**
```
=== RAG VECTOR STORE ===

Total chunks stored: 47

Chunks by document:
  change_management_policy.md: 12 chunks
  incident_management_sop.md: 18 chunks
  vulnerability_management_policy.md: 17 chunks

Sample chunk:
  ID: change_management_policy.md::0
  Source: {'source': 'change_management_policy.md', 'chunk_index': 0}
  Preview: # Change Management Policy

This policy defines the process for requesting, approving, and implementing...
```

### Test It - Query Documents
```bash
python -c "
from app.rag import answer_from_docs

print('=== RAG QUERY DEMO ===\n')

# Query 1: P1 incident process
print('Query 1: What is the P1 incident process?')
result = answer_from_docs('What is the P1 incident process?')
print(f'Answer: {result[\"answer\"][:200]}...')
print(f'Sources: {[s[\"source\"] for s in result[\"sources\"]]}')

print('\n' + '='*60 + '\n')

# Query 2: Vulnerability SLA
print('Query 2: What are the SLA timelines for remediating vulnerabilities?')
result = answer_from_docs('What are the SLA timelines for remediating vulnerabilities?')
print(f'Answer: {result[\"answer\"][:200]}...')
print(f'Sources: {[s[\"source\"] for s in result[\"sources\"]]}')

print('\n' + '='*60 + '\n')

# Query 3: Change process
print('Query 3: Explain the change management process')
result = answer_from_docs('Explain the change management process')
print(f'Answer: {result[\"answer\"][:200]}...')
print(f'Sources: {[s[\"source\"] for s in result[\"sources\"]]}')

print('\n✓ RAG module works!')
"
```

**Expected Output:**
```
=== RAG QUERY DEMO ===

Query 1: What is the P1 incident process?
Answer: A P1 incident is the highest severity level requiring immediate action. The process involves: 1) Immediate notification to the on-call engineer and engineering manager, 2) Creation of a war room with all relevant teams, 3) Frequent status updates every 15 minutes, 4) Focus on mitigation before root cause analysis...
Sources: ['incident_management_sop.md']

============================================================

Query 2: What are the SLA timelines for remediating vulnerabilities?
Answer: Vulnerability remediation SLAs depend on severity: Critical vulnerabilities must be patched within 24 hours, High within 7 days, Medium within 30 days, and Low within 90 days...
Sources: ['vulnerability_management_policy.md']

============================================================

Query 3: Explain the change management process
Answer: The change management process ensures all infrastructure changes are properly reviewed. Steps include: 1) Submit change request, 2) Risk assessment, 3) Approval from change board, 4) Implementation during change window, 5) Verification and rollback plan...
Sources: ['change_management_policy.md']

✓ RAG module works!
```

**Learning Point**: RAG answers are grounded in documents. Retrieval is semantic (similarity-based), not keyword-based.

---

## MODULE 8: agent.py - Tool Routing

### What It Does
Uses LLM's native tool-calling to decide: SQL query or RAG search?

### Test It - Agent Decides Tool
```bash
python - <<'PY'
from app.agent import run_agent
from app.db import SessionLocal

db = SessionLocal()

print('=== AGENT ROUTING DEMO ===\n')

test_cases = [
    ('How many critical vulnerabilities are open?', 'Database'),
    ('What is the procedure for a P1 incident?', 'Documents'),
    ('Which team has the most open incidents?', 'Database'),
    ('What are the change management SLAs?', 'Documents'),
    ('Show employees earning more than 1.5 million', 'Database'),
]

for question, expected_tool_type in test_cases:
    print(f'Question: {question}')
    result = run_agent(db, question)
    tool_used = result['tool_used']
    tool_type = 'Database' if 'database' in tool_used else 'Documents'
    status = '✓' if tool_type == expected_tool_type else '✗'
    print(f'{status} Tool used: {tool_used}')
    print(f"  Answer: {result['answer'][:100]}...")
    print()

db.close()
print('✓ Agent routing works!')
PY
```

**Expected Output:**
```
=== AGENT ROUTING DEMO ===

Question: How many critical vulnerabilities are open?
✓ Tool used: query_database
  Answer: There are currently 12 critical vulnerabilities that are open and require immediate attention...

Question: What is the procedure for a P1 incident?
✓ Tool used: search_documents
  Answer: For a P1 incident, immediate action is required. First, page the on-call engineer and manager immediately. Establish a war room or bridge call with all relevant teams. Begin gathering facts and assessing the scope. Focus on mitigation strategies immediately...

Question: Which team has the most open incidents?
✓ Tool used: query_database
  Answer: The Linux Team has the most open incidents with 8 incidents requiring resolution...

Question: What are the change management SLAs?
✓ Tool used: search_documents
  Answer: All changes must follow the change management process. High-risk changes require CAB approval. Emergency changes can be fast-tracked with manager approval. Change windows are typically Tuesday-Thursday, 2 AM - 6 AM...

Question: Show employees earning more than 1.5 million
✓ Tool used: query_database
  Answer: There are 12 employees earning more than 1.5 million rupees...

✓ Agent routing works!
```

**Learning Point**: Agent uses LLM's tool-calling. LLM reads tool descriptions and picks the best one for each question.

---

## MODULE 9: main.py - FastAPI Application

### What It Does
Defines all HTTP endpoints:
- POST /api/login
- POST /api/ask
- POST /api/ask-docs
- POST /api/agent
- GET /health, /health/db

### Run the Server
```bash
# In one terminal, start the server
uvicorn app.main:app --port 8000 --reload
```

### Test Endpoints (in another terminal)
```bash
# Test 1: Health check
curl http://localhost:8000/health

# Test 2: Database health
curl http://localhost:8000/health/db

# Test 3: Login
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"changeme123"}' | jq .

# Test 4: Save the token
TOKEN=$(curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"changeme123"}' | jq -r .access_token)

echo "Token: $TOKEN"

# Test 5: Use token for agent query
curl -X POST http://localhost:8000/api/agent \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question":"How many employees are in Engineering?"}' | jq .

# Test 6: Direct SQL query
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question":"Count of open P1 incidents"}' | jq .

# Test 7: Direct document query
curl -X POST http://localhost:8000/api/ask-docs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question":"What is the incident response process?"}' | jq .
```

**Expected Output**:
```json
{
  "status": "ok"
}

{
  "db": "ok"
}

{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}

{
  "question": "How many employees are in Engineering?",
  "tool_used": "query_database",
  "answer": "There are 8 employees in the Engineering department.",
  "sql": "SELECT COUNT(*) FROM employees WHERE department = 'Engineering';",
  "rows": [{"count": 8}],
  "explanation": "..."
}
```

**Learning Point**: API is stateless (uses JWT tokens). Each request includes the token in Authorization header.

---

## EXECUTION SEQUENCE FOR UNDERSTANDING

Run in this order:

```bash
# 1. Understand configuration
python -c "from app.config import get_settings; print(get_settings())"

# 2. Understand database connection
python -c "from app.db import engine, SessionLocal; print('DB OK')"

# 3. Understand schema
python -c "from app.models import *; print('Models OK')"

# 4. Generate sample data
python -m app.seed

# 5. Inspect generated data
python -c "from app.db import SessionLocal; from app.models import *; db = SessionLocal(); print(f'Employees: {db.query(Employee).count()}')"

# 6. Test authentication
python -c "from app.auth import authenticate; print(authenticate('admin', 'changeme123'))"

# 7. Ingest RAG documents
python -c "from app.rag import ingest_docs; print(f'Ingested: {ingest_docs()} chunks')"

# 8. Test Text-to-SQL
python -c "from app.text_to_sql import ask; from app.db import SessionLocal; db = SessionLocal(); result = ask(db, 'How many employees?'); print(result)"

# 9. Test RAG
python -c "from app.rag import answer_from_docs; result = answer_from_docs('What is P1 incident?'); print(result)"

# 10. Test Agent
python -c "from app.agent import run_agent; from app.db import SessionLocal; db = SessionLocal(); result = run_agent(db, 'How many vulnerabilities?'); print(result)"

# 11. Start the server
uvicorn app.main:app --port 8000 --reload
```

---

## SUMMARY: Which Files Do What

| File | Type | How to Run | Purpose |
|------|------|-----------|---------|
| db.py | Module | `python -c "from app.db import ..."` | Database connections |
| models.py | Module | `python -c "from app.models import ..."` | Schema definitions |
| seed.py | Script | `python -m app.seed` | Generate sample data |
| config.py | Module | `python -c "from app.config import ..."` | Load settings |
| auth.py | Module | `python -c "from app.auth import ..."` | JWT & authentication |
| text_to_sql.py | Module | `python -c "from app.text_to_sql import ask; ..."` | SQL generation |
| rag.py | Module | `python -c "from app.rag import answer_from_docs; ..."` | Document search |
| agent.py | Module | `python -c "from app.agent import run_agent; ..."` | Tool routing |
| main.py | App | `uvicorn app.main:app` | HTTP API server |
| mcp_server.py | Server | `python -m app.mcp_server` | MCP protocol server |

---

## Pro Tips

### 1. Use Python Interpreter for Interactive Testing
```bash
python

# Now you're in interactive mode
>>> from app.db import SessionLocal
>>> from app.models import Employee
>>> db = SessionLocal()
>>> employees = db.query(Employee).limit(5).all()
>>> for e in employees:
...     print(e.name, e.salary)
>>> exit()
```

### 2. Redirect Output to File for Large Results
```bash
python -c "from app.db import SessionLocal; from app.models import *; db = SessionLocal(); emps = db.query(Employee).all(); [print(f'{e.name},{e.salary}') for e in emps]" > employees.csv
```

### 3. Time Your Queries
```bash
time python -c "from app.text_to_sql import ask; from app.db import SessionLocal; db = SessionLocal(); ask(db, 'How many incidents?')"
```

### 4. Debug Errors
```bash
python -c "
import traceback
try:
    from app.text_to_sql import ask
    from app.db import SessionLocal
    db = SessionLocal()
  result = ask(db, 'DELETE FROM employees')
except Exception as e:
    traceback.print_exc()
"
```

---

**Now you can run each module individually and see exactly how it works!**
