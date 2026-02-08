from google import genai

from app.core.config import get_settings
from app.core.database import get_db
from app.core.llm import get_gemini_client
from app.storage.base import FileStorage
from app.storage.chroma import ChromaVectorStore
from app.storage.local import LocalFileStorage
from app.storage.vector_store import VectorStore

__all__ = ["get_db", "get_file_storage", "get_llm_client", "get_vector_store"]


def get_file_storage() -> FileStorage:
    settings = get_settings()
    return LocalFileStorage(settings.upload_dir)


def get_llm_client() -> genai.Client:
    return get_gemini_client()


def get_vector_store() -> VectorStore:
    settings = get_settings()
    return ChromaVectorStore(host=settings.chromadb_host, port=settings.chromadb_port)
