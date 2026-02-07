from app.core.config import get_settings
from app.core.database import get_db
from app.storage.base import FileStorage
from app.storage.local import LocalFileStorage

__all__ = ["get_db", "get_file_storage"]


def get_file_storage() -> FileStorage:
    settings = get_settings()
    return LocalFileStorage(settings.upload_dir)
