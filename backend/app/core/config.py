"""Environment-driven configuration.

All settings come from environment variables (or a local ``.env`` file). Nothing
is hard-coded, so the same image runs in dev, test and production. See
``.env.example`` for every variable and ``AGENT.md`` for the explanation.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database ---
    # SQLite by default (zero setup). PostgreSQL in Docker/prod, e.g.
    # postgresql+psycopg://app:app@db:5432/appdb
    database_url: str = "sqlite:///./dev.db"

    # --- Security ---
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 60
    jwt_algorithm: str = "HS256"

    # --- App ---
    environment: str = "development"
    # NoDecode: accept a comma-separated string instead of requiring JSON.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Allow CORS_ORIGINS as a comma-separated string in the environment."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read once per process)."""
    return Settings()


settings = get_settings()
