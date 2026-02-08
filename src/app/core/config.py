from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
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

    # AI / Gemini
    google_ai_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "gemini-embedding-001"

    # ChromaDB
    chromadb_host: str = "localhost"
    chromadb_port: int = 8001
    chromadb_collection_resumes: str = "resumes"
    chromadb_collection_jobs: str = "jobs"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
