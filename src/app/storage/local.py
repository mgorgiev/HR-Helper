import asyncio
from pathlib import Path

from app.storage.base import FileStorage


class LocalFileStorage(FileStorage):
    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, file_content: bytes, filename: str, subdir: str = "") -> str:
        target_dir = self.base_dir / subdir
        await asyncio.to_thread(target_dir.mkdir, parents=True, exist_ok=True)
        file_path = target_dir / filename
        await asyncio.to_thread(file_path.write_bytes, file_content)
        return str(Path(subdir) / filename) if subdir else filename

    async def retrieve(self, file_path: str) -> Path:
        abs_path = self.base_dir / file_path
        if not await asyncio.to_thread(abs_path.exists):
            raise FileNotFoundError(f"File not found: {file_path}")
        return abs_path

    async def delete(self, file_path: str) -> None:
        abs_path = self.base_dir / file_path
        if await asyncio.to_thread(abs_path.exists):
            await asyncio.to_thread(abs_path.unlink)

    async def exists(self, file_path: str) -> bool:
        abs_path = self.base_dir / file_path
        return await asyncio.to_thread(abs_path.exists)
