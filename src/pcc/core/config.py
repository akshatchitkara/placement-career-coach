"""Application settings, loaded from environment variables (PCC_ prefix) and .env."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PCC_", env_file=".env", extra="ignore")

    env: str = "local"
    ai_mode: str = "mock"  # mock | live
    ai_api_key: str = "changeme"
    ai_model_name: str = "changeme"
    ai_timeout_seconds: int = 30
    db_path: str = "./data/runtime/pcc.db"
    log_level: str = "INFO"
    demo_mode: bool = Field(default=False)


settings = Settings()
