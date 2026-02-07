"""Unit tests for Settings configuration."""

import pytest

from app.core.config import Settings


@pytest.mark.unit
class TestSettings:
    def test_default_settings(self) -> None:
        """Check that default values are correct."""
        settings = Settings(
            _env_file=None,  # Prevent reading .env file during tests
        )
        assert settings.app_name == "HR Recruitment Assistant"
        assert settings.app_version == "0.1.0"
        assert settings.debug is False
        assert settings.port == 8000
        assert settings.host == "0.0.0.0"
        assert settings.max_upload_size_mb == 10
        assert settings.upload_dir == "./uploads"

    def test_settings_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Override env vars and verify settings pick them up."""
        monkeypatch.setenv("APP_NAME", "Test App")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("PORT", "9000")
        monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "25")
        monkeypatch.setenv("HOST", "127.0.0.1")
        monkeypatch.setenv("UPLOAD_DIR", "/tmp/test_uploads")

        settings = Settings(
            _env_file=None,  # Prevent reading .env file during tests
        )
        assert settings.app_name == "Test App"
        assert settings.debug is True
        assert settings.port == 9000
        assert settings.max_upload_size_mb == 25
        assert settings.host == "127.0.0.1"
        assert settings.upload_dir == "/tmp/test_uploads"

    def test_allowed_extensions_set(self) -> None:
        """The allowed_extensions default should include .pdf, .docx, .txt."""
        settings = Settings(
            _env_file=None,  # Prevent reading .env file during tests
        )
        assert ".pdf" in settings.allowed_extensions
        assert ".docx" in settings.allowed_extensions
        assert ".txt" in settings.allowed_extensions
        assert isinstance(settings.allowed_extensions, set)
