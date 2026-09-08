from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AskVer API"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/askver_db"

    # JWT Settings
    JWT_SECRET_KEY: str = "CHANGE_THIS_TO_A_VERY_SECURE_SECRET_KEY_IN_PRODUCTION"
    JWT_REFRESH_SECRET_KEY: str = "CHANGE_THIS_TO_ANOTHER_VERY_SECURE_SECRET_KEY"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 mins
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7    # 7 days

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()