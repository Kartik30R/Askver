from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    PROJECT_NAME: str = "AskVer API"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL : str ="postgresql+asyncpg://postgres:postgres123@localhost:5433/askver_db"
    CHECKPOINT_DATABASE_URL: str ="postgresql://postgres:postgres123@localhost:5433/askver_db"


    # JWT Settings
    JWT_SECRET_KEY: str = "CHANGE_THIS_TO_A_VERY_SECURE_SECRET_KEY_IN_PRODUCTION"
    JWT_REFRESH_SECRET_KEY: str = "CHANGE_THIS_TO_ANOTHER_VERY_SECURE_SECRET_KEY"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1000
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Embeddings (Google Gemini)
    GEMINI_API_KEY: str | None = None

    # Default LLM provider selection
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-3.5-flash-lite"
    LLM_MODEL_CHEAP: str | None = None
    LLM_MODEL_STRONG: str | None = None
    # "gemini-3.8-flash"

    # Search provider configuration
    TAVILY_API_KEY: str | None = None

    # NVIDIA NIM / OpenAI-compatible API
    NVIDIA_API_KEY: str | None = None
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
        extra="ignore",
    )


settings = Settings()
