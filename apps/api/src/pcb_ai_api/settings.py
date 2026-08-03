"""Application settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PCB_AI_", env_file=".env", extra="ignore")

    app_name: str = "PCB Copilot API"
    environment: str = "local"
    database_url: str = "postgresql+psycopg://pcb:pcb@localhost:5432/pcb_ai"
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "pcbai"
    s3_secret_key: str = "pcbai-secret"
    s3_bucket: str = "pcb-ai"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
