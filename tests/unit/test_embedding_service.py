"""Unit tests for embedding service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.embedding_service import (
    _build_resume_text,
    embed_job,
    embed_resume,
    generate_embedding,
)


def _make_embed_response(values: list[float]) -> MagicMock:
    embedding = MagicMock()
    embedding.values = values

    result = MagicMock()
    result.embeddings = [embedding]
    return result


@pytest.mark.unit
class TestGenerateEmbedding:
    @pytest.mark.asyncio
    async def test_generate_embedding_returns_floats(self) -> None:
        client = MagicMock()
        client.aio.models.embed_content = AsyncMock(
            return_value=_make_embed_response([0.1, 0.2, 0.3])
        )

        result = await generate_embedding(client, "hello", "text-embedding-004")
        assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_generate_embedding_passes_task_type(self) -> None:
        client = MagicMock()
        client.aio.models.embed_content = AsyncMock(return_value=_make_embed_response([0.5]))

        await generate_embedding(client, "text", "text-embedding-004", task_type="RETRIEVAL_QUERY")

        call_kwargs = client.aio.models.embed_content.call_args
        assert call_kwargs.kwargs["config"]["task_type"] == "RETRIEVAL_QUERY"


@pytest.mark.unit
class TestBuildResumeText:
    def test_builds_text_from_parsed_data(self) -> None:
        parsed = {
            "summary": "Experienced developer",
            "skills": ["Python", "FastAPI"],
            "experience": [
                {"title": "Dev", "company": "Acme", "description": "Built APIs"},
            ],
            "education": [
                {"degree": "BS", "field": "CS", "institution": "MIT"},
            ],
        }
        text = _build_resume_text(parsed)
        assert "Experienced developer" in text
        assert "Python, FastAPI" in text
        assert "Dev at Acme" in text
        assert "BS in CS from MIT" in text

    def test_handles_empty_data(self) -> None:
        text = _build_resume_text({})
        assert text == "No resume data available"

    def test_handles_missing_fields(self) -> None:
        parsed = {"skills": ["Python"]}
        text = _build_resume_text(parsed)
        assert "Python" in text


@pytest.mark.unit
class TestEmbedResume:
    @pytest.mark.asyncio
    async def test_embed_resume_calls_generate(self) -> None:
        client = MagicMock()
        client.aio.models.embed_content = AsyncMock(return_value=_make_embed_response([0.1, 0.2]))

        result = await embed_resume(client, "text-embedding-004", {"skills": ["Python"]})
        assert result == [0.1, 0.2]
        client.aio.models.embed_content.assert_called_once()


@pytest.mark.unit
class TestEmbedJob:
    @pytest.mark.asyncio
    async def test_embed_job_calls_generate(self) -> None:
        client = MagicMock()
        client.aio.models.embed_content = AsyncMock(return_value=_make_embed_response([0.3, 0.4]))

        result = await embed_job(client, "text-embedding-004", "Dev", "Build APIs", "Python")
        assert result == [0.3, 0.4]
        client.aio.models.embed_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_job_handles_none_fields(self) -> None:
        client = MagicMock()
        client.aio.models.embed_content = AsyncMock(return_value=_make_embed_response([0.5]))

        result = await embed_job(client, "text-embedding-004", "Dev", None, None)
        assert result == [0.5]
