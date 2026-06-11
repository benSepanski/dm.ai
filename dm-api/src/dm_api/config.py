from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Set ANTHROPIC_API_KEY in .env when AI_PROVIDER="anthropic" (the default).
    anthropic_api_key: str = ""
    database_url: str = "postgresql+asyncpg://dmuser:dmpass@localhost:5432/dmdb"
    redis_url: str = "redis://localhost:6379"
    secret_key: str = "dev-secret-key"
    frontend_url: str = "http://localhost:5173"

    # Shared token that unlocks the DM role (X-DM-Token header / dm_token WS
    # query param). Leave empty to auto-generate one per run — it is printed
    # in the API startup logs.
    dm_token: str = ""

    # AI provider: "anthropic" (uses ANTHROPIC_API_KEY) or "claude_cli" (uses installed claude CLI)
    ai_provider: Literal["anthropic", "claude_cli"] = "anthropic"

    # Model roles - override per-environment to tune cost/capability tradeoffs
    # Used for quick tasks: session summaries, NPC dialogue snippets, flavor text
    generation_model: str = "claude-haiku-4-5-20251001"
    # Main orchestrator model (used for session chat responses)
    orchestrator_model: str = "claude-sonnet-4-6"

    # Context window management
    context_token_limit: int = 180_000  # trigger summarization at 80% of 200k
    context_preserve_last_n: int = 5

    # Logging — set LOG_LEVEL=DEBUG to see AI call details and token counts
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


settings = Settings()
