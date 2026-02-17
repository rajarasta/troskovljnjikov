from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/boq.db"
    LLM_BASE_URL: str = "http://localhost:8095/v1"
    LLM_MODEL_NAME: str = "ministral-3b"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    MAX_UPLOAD_SIZE_MB: int = 50
    MATCH_THRESHOLD: float = 0.3
    MAX_MATCH_RESULTS: int = 20

    model_config = {"env_file": ".env"}


settings = Settings()
