"""Unit tests for resume parsing service."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.parsed_resume import ParsedResumeData
from app.services.resume_parser import parse_resume


def _make_gemini_response(data: dict) -> MagicMock:
    """Create a mock Gemini response with JSON text."""
    response = MagicMock()
    response.text = json.dumps(data)
    return response


@pytest.mark.unit
class TestParseResume:
    @pytest.mark.asyncio
    async def test_parse_resume_returns_structured_data(self) -> None:
        data = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "skills": ["Python", "FastAPI"],
            "experience": [{"company": "Acme", "title": "Dev", "description": "Built APIs"}],
            "education": [{"institution": "MIT", "degree": "BS", "field": "CS"}],
        }

        client = MagicMock()
        client.aio.models.generate_content = AsyncMock(return_value=_make_gemini_response(data))

        result = await parse_resume(client, "Some resume text", "gemini-2.0-flash")

        assert isinstance(result, ParsedResumeData)
        assert result.full_name == "John Doe"
        assert result.skills == ["Python", "FastAPI"]
        assert len(result.experience) == 1
        assert result.experience[0].company == "Acme"
        assert len(result.education) == 1

    @pytest.mark.asyncio
    async def test_parse_resume_empty_response(self) -> None:
        response = MagicMock()
        response.text = None

        client = MagicMock()
        client.aio.models.generate_content = AsyncMock(return_value=response)

        result = await parse_resume(client, "text", "gemini-2.0-flash")
        assert isinstance(result, ParsedResumeData)
        assert result.full_name is None
        assert result.skills == []

    @pytest.mark.asyncio
    async def test_parse_resume_minimal_response(self) -> None:
        data = {"full_name": "Jane"}

        client = MagicMock()
        client.aio.models.generate_content = AsyncMock(return_value=_make_gemini_response(data))

        result = await parse_resume(client, "text", "gemini-2.0-flash")
        assert result.full_name == "Jane"
        assert result.skills == []
        assert result.experience == []
