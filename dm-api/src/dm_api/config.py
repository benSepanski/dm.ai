from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    database_url: str = "postgresql+asyncpg://dmuser:dmpass@localhost:5432/dmdb"
    redis_url: str = "redis://localhost:6379"
    secret_key: str = "dev-secret-key"
    frontend_url: str = "http://localhost:5173"

    # AI model choices
    orchestrator_model: str = "claude-opus-4-6"
    fast_model: str = "claude-haiku-4-5-20251001"

    # Context window management
    context_token_limit: int = 180_000  # trigger summarization at 80% of 200k
    context_preserve_last_n: int = 5


settings = Settings()
