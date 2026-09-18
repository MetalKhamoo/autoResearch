"""
config/settings.py
──────────────────
Central settings module using Pydantic-Settings v2.
Loads from environment variables and an optional .env file.
All other modules import from here — never read os.environ directly.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProviderName(str, Enum):
    anthropic = "anthropic"
    openai = "openai"


class SearchProviderName(str, Enum):
    duckduckgo = "duckduckgo"
    serpapi = "serpapi"


class LogLevel(str, Enum):
    debug = "DEBUG"
    info = "INFO"
    warning = "WARNING"
    error = "ERROR"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_provider: LLMProviderName = LLMProviderName.anthropic
    llm_model: str = "claude-sonnet-5"  # claude-opus-5 for max capability; claude-haiku-4-5-20251001 for speed
    anthropic_api_key: str | None = Field(default=None)
    openai_api_key: str | None = Field(default=None)

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./autoresearch.db"

    # ── Vector Store ─────────────────────────────────────────────────────────
    chroma_persist_dir: str = "./chroma_data"
    chroma_collection_name: str = "autoresearch_docs"

    # ── Web Search ───────────────────────────────────────────────────────────
    search_provider: SearchProviderName = SearchProviderName.duckduckgo
    serpapi_key: str | None = Field(default=None)
    max_search_results: int = 10

    # ── RAG ──────────────────────────────────────────────────────────────────
    rag_top_k: int = 5

    # ── Scheduler ────────────────────────────────────────────────────────────
    scheduler_timezone: str = "UTC"

    # ── API ──────────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: LogLevel = LogLevel.info

    # ── Derived helpers ───────────────────────────────────────────────────────
    @field_validator("chroma_persist_dir", mode="before")
    @classmethod
    def resolve_chroma_path(cls, v: str) -> str:
        return str(Path(v).resolve())

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
