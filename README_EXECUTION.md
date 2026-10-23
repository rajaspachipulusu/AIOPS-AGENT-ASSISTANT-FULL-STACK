# Project Understanding & Execution Flow - Summary

## What You Now Have

I've created **4 comprehensive documents** to help you understand and execute this fullstack AI application:

### 1. **AGENTS.md** (Root Directory)
**Purpose**: AI Agent customization guide for understanding the codebase
- Complete project architecture overview
- Technology stack table
- Step-by-step execution flow with explanations
- Core processing flows (Text-to-SQL, RAG, Agent routing)
- Key files & purposes table
- Testing instructions
- Common development tasks
- MCP server advanced usage
- Troubleshooting guide

**Use This When**: You need to understand the system architecture, file structure, and typical development tasks

---

### 2. **EXECUTION_FLOW.md** (Root Directory)
**Purpose**: Detailed step-by-step execution with deep learning points
- 9 phases of execution (prerequisites through testing)
- Each step includes:
  - Exact command
  - Expected output
  - Why it matters
  - Learning point (key insight)
- Deep dive into each module (Text-to-SQL, RAG, Agent, Models, Auth)
- Manual testing procedures for each component
- Production checklist
- Summary table showing execution order

**Use This When**: You're actually executing the commands and want to understand what's happening at each step

---

### 3. **COMMANDS_REFERENCE.md** (Root Directory)
**Purpose**: Quick copy-paste reference for all commands
- Commands organized by phase
- Commands for testing each module
- Environment variables reference
- Troubleshooting commands
- One-liner startup
- API testing with curl
- Learning order recommendation

**Use This When**: You just need the commands quickly without detailed explanations

---

### 4. **Architecture Memory** (Session Memory)
- Core components and their purposes
- Technology stack summary
- Critical dependencies
- Key processing modules

---

## Execution Summary in 10 Steps

| Step | Command | What Happens | Time |
|------|---------|---|------|
| 1 | Verify prerequisites (Python, Node, Postgres, Ollama) | Ensure all services are available | 5 min |
| 2 | `cd backend && source .venv/bin/activate` | Activate Python environment | 1 min |
| 3 | `pip install -r requirements.txt` | Install Python dependencies | 5 min |
| 4 | Run DB init and seed scripts | Create tables and sample data (200 records) | 3 min |
| 5 | `python -c "from app.rag import ingest_docs; ingest_docs()"` | Embed documents for RAG | 3 min |
| 6 | `uvicorn app.main:app --port 8000 --reload` | Start backend API (keep running) | 2 min |
| 7 | Open new terminal, `cd frontend && npm install` | Install Node dependencies | 3 min |
| 8 | `npm run dev` | Start frontend (keep running) | 2 min |
| 9 | Open `http://localhost:3000` in browser | Login with admin/changeme123 | 1 min |
| 10 | Ask a question (e.g., "How many vulnerabilities?") | See full pipeline working | 1 min |

**Total Time**: ~26 minutes (first setup)
**Subsequent Runs**: ~5 minutes (just restart servers)

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────┐
│              Frontend (Next.js)                      │
│            http://localhost:3000                     │
│  Chat UI + Login Form + Result Display              │
└────────────────┬────────────────────────────────────┘
                 │ HTTP/JSON
                 │
┌────────────────▼────────────────────────────────────┐
│           Backend API (FastAPI)                      │
│            http://localhost:8000                     │
│  /api/login, /api/agent, /api/ask, /api/ask-docs    │
│                                                      │
│  Routes to:                                         │
│  ├─ text_to_sql.py   (Question → SQL → Execute)   │
│  ├─ rag.py           (Question → Retrieve Docs)    │
│  └─ agent.py         (Decide: SQL or RAG?)         │
└──┬───────────────────────────────────────────────┬──┘
   │                                               │
   │ SQL                                           │ Embeddings
   │                                               │
┌──▼──────────────────────────────────┐  ┌────────▼────────────────┐
│  PostgreSQL                          │  │  Ollama (Local LLM)     │
│  http://localhost:5432              │  │  http://localhost:11434 │
│                                      │  │                         │
│ ├─ employees (40)                   │  │ ├─ qwen3:8b (LLM)       │
│ ├─ servers (25)                     │  │ └─ nomic-embed-text     │
│ ├─ incidents (60)                   │  │ (embeddings)            │
│ └─ vulnerabilities (80)             │  │                         │
│                                      │  │ Used for:              │
│ Guardrails:                          │  │ - SQL generation       │
│ - Read-only role (aiops_reader)     │  │ - Result explanation   │
│ - 5s timeout                         │  │ - Tool routing         │
│ - SQL validation                     │  │ - Embedding docs       │
└──────────────────────────────────────┘  └────────────────────────┘
         │
         ▼
      ┌──────────────────────────┐
      │  ChromaDB Vector Store   │
      │  backend/chroma_store/   │
      │                          │
      │ Stores embeddings for:   │
      │ - change_management.md   │
      │ - incident_management.md │
      │ - vulnerability_policy.md│
      └──────────────────────────┘
```

---

## Three Core Processing Flows

### Flow 1: Text-to-SQL (Structured Data)
```
User: "How many critical vulnerabilities are open?"
  ↓
LLM Generates SQL: SELECT COUNT(*) FROM vulnerabilities 
                   WHERE severity='Critical' AND status='open'
  ↓
Validation: Check for forbidden keywords (INSERT, DELETE, etc.)
  ↓
Execute: Run against read-only PostgreSQL role
  ↓
LLM Explains: "There are currently 12 critical vulnerabilities..."
  ↓
Return: {question, sql, rows: [{count: 12}], explanation}
```

**Key Guardrails**:
- SQL statement validation (forbid INSERT/UPDATE/DELETE)
- Read-only PostgreSQL role (prevents writes even if SQL passes)
- 5-second timeout (DOS protection)
- Max 200 rows (data exfiltration protection)

---

### Flow 2: RAG (Document Search)
```
User: "What is the P1 incident process?"
  ↓
Embed Question: Convert to 768-dim vector using nomic-embed-text
  ↓
Retrieve Chunks: ChromaDB finds top-4 most similar document chunks
  ↓
Build Context: Concatenate retrieved chunks
  ↓
LLM Answers: Using ONLY the provided context, answer the question
  ↓
Return: {question, answer, sources: [{filename, chunk_index}]}
```

**Key Design**:
- Answers are **grounded** in documents (prevents hallucination)
- Documents are chunked and embedded (800 chars/chunk)
- Similarity-based retrieval (semantic, not keyword)

---

### Flow 3: Agent Routing (Hybrid)
```
User: Question (could be about data or procedures)
  ↓
LLM Sees Two Tools: "query_database" or "search_documents"
  ↓
LLM Decides: Which tool is better for this question?
  ↓
Execute Chosen Tool: Call text_to_sql OR rag
  ↓
Return: {question, tool_used, answer, ...tool-specific fields}
```

**Current State**: Single-step routing (one tool per question)
**Future**: Multi-step routing (call both tools, synthesize results)

---

## Learning Progression

### Level 1: Get It Running (1 hour)
- [ ] Verify all prerequisites
- [ ] Setup backend
- [ ] Start backend API
- [ ] Setup frontend
- [ ] Ask your first question

**Outcome**: See the full pipeline working end-to-end

---

### Level 2: Understand Each Component (2 hours)
- [ ] Read AGENTS.md architecture section
- [ ] Read each module section in EXECUTION_FLOW.md:
  - Text-to-SQL: How SQL is generated, validated, executed
  - RAG: How documents are ingested and retrieved
  - Agent: How tool routing works
  - Frontend: How components communicate with backend
- [ ] Run manual tests for each module
- [ ] Run pytest to verify guardrails

**Outcome**: Deep understanding of how each piece works

---

### Level 3: Extend & Customize (3-4 hours)
- [ ] Add a new document to RAG and re-ingest
- [ ] Modify guardrails (add forbidden keywords, change row limit)
- [ ] Add a new API endpoint
- [ ] Add a new tool to the agent
- [ ] Modify the LLM prompt to be more specific
- [ ] Update demo credentials in .env

**Outcome**: Can modify system to meet specific needs

---

### Level 4: Production Readiness (4-6 hours)
- [ ] Review production checklist in EXECUTION_FLOW.md Phase 9
- [ ] Implement secret management
- [ ] Add token expiration logic
- [ ] Setup error tracking (Sentry, DataDog)
- [ ] Setup centralized logging
- [ ] Add rate limiting
- [ ] Containerize with Docker
- [ ] Setup CI/CD pipeline

**Outcome**: Ready for production deployment

---

## Key Files to Know

| File | Purpose | Key Insight |
|------|---------|---|
| `backend/app/main.py` | API routes | Define endpoints with Pydantic models |
| `backend/app/text_to_sql.py` | SQL generation & execution | LLM generates SQL, validation checks for attacks |
| `backend/app/rag.py` | Document search | Embeddings + ChromaDB for semantic retrieval |
| `backend/app/agent.py` | Tool routing | LLM decides which tool to use |
| `backend/app/models.py` | Database schema | SQLAlchemy models (source of truth) |
| `backend/app/seed.py` | Sample data | Generates realistic demo data |
| `backend/app/db.py` | Connections | Two engines: full + read-only |
| `frontend/src/app/page.tsx` | Main UI | React hooks for state management |
| `backend/requirements.txt` | Dependencies | Pinned versions for reproducibility |
| `.env` | Configuration | Secrets, credentials, URLs |

---

## Most Important Security Points

1. **Read-only Database Role**: LLM SQL is executed by `aiops_reader` (SELECT only, no writes)
2. **SQL Validation**: Forbidden keywords checked before execution
3. **Statement Timeout**: 5-second limit prevents DOS
4. **Row Limits**: Max 200 rows prevents data exfiltration
5. **Token-Based Auth**: JWT tokens, no password stored after login
6. **Dependency Pinning**: requirements.txt pins exact versions (reproducible builds)

---

## Troubleshooting Map

| Symptom | Most Likely Cause | Fix |
|---------|---|---|
| "Cannot reach Ollama" | Ollama not running | `ollama serve` |
| "Module not found" errors | Venv not activated | `source .venv/bin/activate` |
| "Database connection refused" | Postgres not running | `brew services start postgresql@16` |
| "Frontend can't reach backend" | CORS or backend down | Check `curl http://localhost:8000/health` |
| "ChromaDB errors" | RAG not ingested | Run `python -c "from app.rag import ingest_docs; ingest_docs()"` |
| "Query returns 'Forbidden keyword'" | SQL contains INSERT/DELETE/etc. | This is intentional security feature |
| "Token expired" | (Currently no expiration) | Refresh by logging in again |

---

## Quick Decision Tree

```
Q: Where do I start?
└─→ A: Read COMMANDS_REFERENCE.md and run Phase 1-5

Q: Something isn't working
└─→ A: Check AGENTS.md Troubleshooting section
    └─→ A2: If not there, check EXECUTION_FLOW.md Phase 6 debugging commands

Q: How does component X work?
└─→ A: Find X in EXECUTION_FLOW.md Phase 7 (modules section)
    └─→ A2: Copy the manual test and run it

Q: What should I modify?
└─→ A: Read "Common Development Tasks" in AGENTS.md
    └─→ A2: Implement change
    └─→ A3: Run pytest to verify nothing broke

Q: Ready for production?
└─→ A: Review Phase 9 Production Checklist in EXECUTION_FLOW.md
```

---

## Next Steps

### Immediate (Now)
1. Read COMMANDS_REFERENCE.md phases 1-5
2. Execute those commands step by step
3. Verify it all works by asking questions in the UI

### Short-term (This week)
1. Read EXECUTION_FLOW.md Phase 7 (module deep-dive)
2. Run the manual tests for each module
3. Modify something small (add a document to RAG, change demo credentials)
4. Run tests to verify nothing broke

### Medium-term (This month)
1. Extend the agent to handle multi-step queries
2. Add guardrails or modify existing ones
3. Deploy to a test environment
4. Collect feedback on user experience

### Long-term (Before production)
1. Implement production checklist
2. Migrate to production database
3. Setup monitoring and logging
4. Conduct security audit
5. Load testing

---

## Document Map

```
fullstack-ai-assistant/
│
├── AGENTS.md ........................ Architecture + Development Guide
├── EXECUTION_FLOW.md .............. Detailed step-by-step with learning points
├── COMMANDS_REFERENCE.md ........... Quick copy-paste command reference
├── REVERSE_ENGINEERING.md ......... Deep technical architecture
│
├── backend/
│   ├── app/
│   │   ├── main.py ................. API routes (start here for endpoints)
│   │   ├── text_to_sql.py ......... SQL generation pipeline
│   │   ├── rag.py ................. Document ingestion & retrieval
│   │   ├── agent.py ............... Tool routing logic
│   │   ├── models.py .............. Database schema
│   │   └── seed.py ................ Sample data generator
│   ├── requirements.txt ............ Python dependencies
│   └── db_init/ .................... Database initialization
│
├── frontend/
│   ├── src/app/
│   │   ├── page.tsx ............... Main chat interface
│   │   ├── LoginForm.tsx .......... Authentication UI
│   │   └── ResultCard.tsx ......... Result display
│   ├── package.json ............... Node.js dependencies
│   └── README.md .................. Frontend-specific guide
│
└── docker-compose.yml ............. Container orchestration
```

---

## Remember

- **Backend must stay running** while you develop
- **Keep venv activated** in terminal
- **Ollama must have models pulled** before starting backend
- **Tests are your safety net** - run them before pushing changes
- **Logs are your friend** - watch the backend terminal for clues
- **Start simple** - get the basic flow working before customizing

---

## You're Ready!

You now have everything needed to:
✅ Understand the architecture
✅ Execute the system step-by-step
✅ Debug when things go wrong
✅ Test each component independently
✅ Extend and customize
✅ Deploy to production

**Start with COMMANDS_REFERENCE.md Phases 1-5 and have fun!**
