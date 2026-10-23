from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Separate engine/session bound to the restricted `aiops_reader` role.
# Used exclusively for executing LLM-generated SQL (Text-to-SQL feature),
# so that even a bug in application-level validation cannot lead to writes.
readonly_engine = create_engine(settings.readonly_database_url, pool_pre_ping=True)
ReadOnlySessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=readonly_engine
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_readonly_db():
    db = ReadOnlySessionLocal()
    try:
        yield db
    finally:
        db.close()
