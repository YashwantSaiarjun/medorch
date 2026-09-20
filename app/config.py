"""
Central configuration for MedOrch.

All configuration is sourced from environment variables so that no secrets
are ever hard-coded in source. See .env.example for the full list of
supported variables.
"""
from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    # --- LLM provider --------------------------------------------------
    llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic")
    llm_api_key: str | None = os.getenv("LLM_API_KEY") or None
    llm_model: str = os.getenv("LLM_MODEL", "claude-sonnet-4-6")

    # --- Database --------------------------------------------------------
    # When DATABASE_URL is set, the Postgres + pgvector backed store is used
    # (this is how docker-compose runs the stack). When it is not set (e.g.
    # local unit tests, or a quick `uvicorn` run without infra), MedOrch
    # falls back to an in-memory vector store that implements the exact
    # same interface. Only the storage backend changes -- the security
    # boundary (which agent may query which store) is identical in both
    # modes.
    database_url: str | None = os.getenv("DATABASE_URL") or None

    # --- App behaviour ---------------------------------------------------
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    retrieval_top_k: int = int(os.getenv("RETRIEVAL_TOP_K", "3"))

    # Disable outbound LLM calls entirely (useful for offline/CI demos).
    # When true, MedOrch uses deterministic heuristic intent-classification
    # and template-based answer synthesis instead of calling the LLM.
    disable_llm: bool = os.getenv("DISABLE_LLM", "false").lower() == "true"


@lru_cache
def get_settings() -> Settings:
    return Settings()
