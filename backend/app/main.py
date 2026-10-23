import logging

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import authenticate, create_access_token, get_current_user
from app.db import get_db, get_readonly_db
from app.logging_config import configure_logging, RequestLoggingMiddleware, logger
from app.text_to_sql import ask, SQLGenerationError, UnsafeSQLError
from app.rag import answer_from_docs
from app.agent import run_agent, AgentError

configure_logging()

app = FastAPI(title="AI Ops Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all so clients always get a consistent JSON error shape, and
    full details are logged server-side rather than leaked to the client."""
    logger.exception(
        "Unhandled exception",
        extra={"extra_fields": {"path": request.url.path}},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again."},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1")).scalar()
    return {"db": "ok" if result == 1 else "error"}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@app.post("/api/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    if not authenticate(payload.username, payload.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(payload.username)
    logger.info(
        "user logged in",
        extra={"extra_fields": {"username": payload.username}},
    )
    return TokenResponse(access_token=token)


class AskRequest(BaseModel):
    question: str


@app.post("/api/ask")
def ask_question(
    payload: AskRequest,
    db: Session = Depends(get_readonly_db),
    user: str = Depends(get_current_user),
):
    try:
        return ask(db, payload.question)
    except UnsafeSQLError as e:
        raise HTTPException(status_code=400, detail=f"Unsafe query blocked: {e}")
    except SQLGenerationError as e:
        raise HTTPException(status_code=422, detail=f"Could not generate SQL: {e}")


@app.post("/api/ask-docs")
def ask_docs(payload: AskRequest, user: str = Depends(get_current_user)):
    """RAG endpoint: answers questions using the enterprise document corpus
    (SOPs, policies) instead of the structured database."""
    return answer_from_docs(payload.question)


@app.post("/api/agent")
def agent_ask(
    payload: AskRequest,
    db: Session = Depends(get_readonly_db),
    user: str = Depends(get_current_user),
):
    """Unified entry point: an agent decides whether to query the database
    (Text-to-SQL) or search enterprise documents (RAG) to answer the
    question, then executes that tool."""
    try:
        return run_agent(db, payload.question)
    except UnsafeSQLError as e:
        raise HTTPException(status_code=400, detail=f"Unsafe query blocked: {e}")
    except SQLGenerationError as e:
        raise HTTPException(status_code=422, detail=f"Could not generate SQL: {e}")
    except AgentError as e:
        raise HTTPException(status_code=500, detail=str(e))
