from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    database_url: str = "postgresql+asyncpg://dmuser:dmpass@localhost:5432/dmdb"
    redis_url: str = "redis://localhost:6379"
    secret_key: str = "dev-secret-key"
    frontend_url: str = "http://localhost:5173"

    # AI provider: "anthropic" (uses ANTHROPIC_API_KEY) or "claude_cli" (uses installed claude CLI)
    ai_provider: str = "anthropic"

    # Model roles - override per-environment to tune cost/capability tradeoffs
    # Used for complex reasoning: narrative generation, world-building, proposal creation
    planning_model: str = "claude-sonnet-4-6"
    # Used for quick tasks: session summaries, NPC dialogue snippets, flavor text
    generation_model: str = "claude-haiku-4-5-20251001"
    # Main orchestrator model (used for session chat responses)
    orchestrator_model: str = "claude-sonnet-4-6"  # updated default from opus
    # Fast model kept for backward compat
    fast_model: str = "claude-haiku-4-5-20251001"

    # Context window management
    context_token_limit: int = 180_000  # trigger summarization at 80% of 200k
    context_preserve_last_n: int = 5


settings = Settings()
