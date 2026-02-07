"""Unit tests for LocalFileStorage."""

from pathlib import Path

import pytest

from app.storage.local import LocalFileStorage


@pytest.mark.unit
class TestLocalFileStorage:
    @pytest.fixture
    def storage(self, tmp_path: Path) -> LocalFileStorage:
        """Create a LocalFileStorage instance rooted in a temp directory."""
        return LocalFileStorage(str(tmp_path / "storage"))

    @pytest.mark.asyncio
    async def test_local_save_creates_file(self, storage: LocalFileStorage, tmp_path: Path) -> None:
        """Saving bytes should create the file on disk."""
        content = b"Hello, this is a test resume."
        relative_path = await storage.save(content, "resume.pdf")

        assert relative_path == "resume.pdf"
        saved_file = storage.base_dir / "resume.pdf"
        assert saved_file.exists()
        assert saved_file.read_bytes() == content

    @pytest.mark.asyncio
    async def test_local_save_with_subdir(self, storage: LocalFileStorage, tmp_path: Path) -> None:
        """Saving with a subdirectory should auto-create the subdirectory."""
        content = b"Nested file content"
        relative_path = await storage.save(content, "doc.pdf", subdir="candidates/123")

        assert relative_path == str(Path("candidates/123") / "doc.pdf")
        saved_file = storage.base_dir / "candidates" / "123" / "doc.pdf"
        assert saved_file.exists()
        assert saved_file.read_bytes() == content

    @pytest.mark.asyncio
    async def test_local_retrieve_returns_path(self, storage: LocalFileStorage) -> None:
        """Retrieving an existing file should return the correct absolute path."""
        content = b"Retrievable content"
        relative_path = await storage.save(content, "findme.txt")

        abs_path = await storage.retrieve(relative_path)
        assert abs_path.is_absolute()
        assert abs_path == storage.base_dir / "findme.txt"
        assert abs_path.exists()

    @pytest.mark.asyncio
    async def test_local_delete_removes_file(self, storage: LocalFileStorage) -> None:
        """Deleting a file should remove it from disk."""
        content = b"Delete me"
        relative_path = await storage.save(content, "deleteme.txt")

        # Verify file exists before deletion
        assert (storage.base_dir / "deleteme.txt").exists()

        await storage.delete(relative_path)

        assert not (storage.base_dir / "deleteme.txt").exists()

    @pytest.mark.asyncio
    async def test_local_exists_true_and_false(self, storage: LocalFileStorage) -> None:
        """exists() should return True for saved files and False for missing ones."""
        assert await storage.exists("nonexistent.pdf") is False

        await storage.save(b"data", "present.pdf")
        assert await storage.exists("present.pdf") is True

    @pytest.mark.asyncio
    async def test_local_retrieve_nonexistent_raises(self, storage: LocalFileStorage) -> None:
        """Retrieving a file that does not exist should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            await storage.retrieve("no_such_file.pdf")
