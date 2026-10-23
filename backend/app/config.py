from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://localhost:5432/aiops"
    # Restricted, read-only role used exclusively for executing LLM-generated
    # SQL. Kept separate from `database_url` (used for app/internal queries)
    # so that a bug in SQL validation cannot cause data modification.
    readonly_database_url: str = (
        "postgresql+psycopg2://aiops_reader:readonly_dev_pw@localhost:5432/aiops"
    )
    app_env: str = "development"

    # Auth (demo single-user setup; see app/auth.py)
    jwt_secret: str = "dev-only-insecure-secret-change-me"
    demo_username: str = "admin"
    demo_password: str = "changeme123"

    # Base URL for the local Ollama server. In local dev this is
    # http://localhost:11434; when the backend runs inside a container it
    # must point at the host (e.g. http://host.containers.internal:11434).
    ollama_base_url: str = "http://localhost:11434"

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()
