from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./data/boq.db"

    # LLM Configuration
    # Local llama-server (fallback/legacy)
    LLM_BASE_URL: str = "http://localhost:8095/v1"  # Deprecated, kept for compatibility
    LLM_MODEL_NAME: str = "ministral-3b"  # Local model name

    # Claude API (primary for search agent tool calling)
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_BASE_URL: str = "https://api.anthropic.com/v1"
    CLAUDE_MODEL: str = "claude-opus-4-6"

    # CORS Configuration
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # File & Matching Configuration
    MAX_UPLOAD_SIZE_MB: int = 50
    MATCH_THRESHOLD: float = 0.3
    MAX_MATCH_RESULTS: int = 20

    # Rate Limiting & Cost Control
    MAX_API_REQUESTS_PER_MINUTE: int = 50
    MAX_TOKENS_PER_DAY: int = 1_000_000
    MAX_COST_PER_DAY_USD: float = 10.0

    model_config = {"env_file": ".env"}


settings = Settings()
