from typing import Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator

class Settings(BaseSettings):
    # Application
    PROJECT_NAME: str = "AI Agent Orchestration Platform"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = Field(default="postgresql://user:password@localhost/dbname", env="DATABASE_URL")

    # Security
    SECRET_KEY: str = Field(default="your-secret-key-here-32-characters-long", env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")

    # CORS
    ALLOWED_ORIGINS: list[str] = ["*"]
    ALLOWED_METHODS: list[str] = ["*"]
    ALLOWED_HEADERS: list[str] = ["*"]

    @validator("SECRET_KEY")
    def secret_key_length(cls, v: Any) -> Any:
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v

    class Config:
        env_file = ".env"

settings = Settings()