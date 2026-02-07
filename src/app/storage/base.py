from abc import ABC, abstractmethod
from pathlib import Path


class FileStorage(ABC):
    @abstractmethod
    async def save(self, file_content: bytes, filename: str, subdir: str = "") -> str:
        """Save file and return the relative file path."""
        ...

    @abstractmethod
    async def retrieve(self, file_path: str) -> Path:
        """Return absolute Path to the stored file."""
        ...

    @abstractmethod
    async def delete(self, file_path: str) -> None:
        """Delete a file from storage."""
        ...

    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        """Check if a file exists in storage."""
        ...
