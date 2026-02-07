from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "HR Recruitment Assistant"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://hr_helper:hr_helper_dev@localhost:5432/hr_helper"

    # File uploads
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 10
    allowed_extensions: set[str] = {".pdf", ".docx", ".txt"}

    # Server
    host: str = "0.0.0.0"
    port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
