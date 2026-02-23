from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://localhost:5432/ai_orchestration"

    # JWT
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS
    cors_origins: List[str] = ["*"]

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # in seconds

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Logging
    log_level: str = "INFO"

    # File Upload
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: List[str] = [".json", ".txt", ".csv", ".xml"]

    # Task Execution
    task_execution_timeout: int = 300  # 5 minutes
    max_concurrent_tasks: int = 10

    # WebSocket
    websocket_ping_interval: int = 30
    websocket_timeout: int = 60

    # API
    api_version: str = "v1"
    base_url: str = "http://localhost:8000"

    # Email (for notifications)
    email_host: Optional[str] = None
    email_port: Optional[int] = None
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_from: Optional[str] = None

    # External Services
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()