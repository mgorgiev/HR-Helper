"""Integration tests for resume parsing endpoints.

Tests exercise POST /resumes/{id}/parse and GET /resumes/{id}/parsed
with a mocked Gemini client and real PostgreSQL database.
"""

import uuid
from pathlib import Path

import pytest

from tests.conftest import make_candidate_payload

pytestmark = pytest.mark.integration

SAMPLE_DIR = Path(__file__).parent.parent.parent / "sample_data" / "resumes"
CANDIDATES_API = "/api/v1/candidates"


async def _create_candidate(client, **overrides):
    payload = make_candidate_payload(**overrides)
    resp = await client.post(CANDIDATES_API, json=payload)
    assert resp.status_code == 201
    return resp.json()


async def _upload_resume(client, candidate_id: str):
    file_path = SAMPLE_DIR / "sample_resume.txt"
    with open(file_path, "rb") as f:
        resp = await client.post(
            f"/api/v1/candidates/{candidate_id}/resumes",
            files={"file": ("sample_resume.txt", f, "text/plain")},
        )
    assert resp.status_code == 201
    return resp.json()


async def test_parse_resume_200(client):
    """POST /resumes/{id}/parse triggers Gemini parsing and saves result."""
    candidate = await _create_candidate(client)
    resume = await _upload_resume(client, candidate["id"])

    resp = await client.post(f"/api/v1/resumes/{resume['id']}/parse")

    assert resp.status_code == 200
    body = resp.json()
    assert body["parsing_status"] == "completed"
    assert body["parsed_data"] is not None
    assert body["parsed_data"]["full_name"] == "John Doe"
    assert "Python" in body["parsed_data"]["skills"]


async def test_parse_resume_not_found_404(client):
    """POST /resumes/{id}/parse with invalid ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(f"/api/v1/resumes/{fake_id}/parse")
    assert resp.status_code == 404


async def test_get_parsed_resume_200(client):
    """GET /resumes/{id}/parsed returns structured data after parsing."""
    candidate = await _create_candidate(client)
    resume = await _upload_resume(client, candidate["id"])

    # Parse first
    parse_resp = await client.post(f"/api/v1/resumes/{resume['id']}/parse")
    assert parse_resp.status_code == 200

    # Then get parsed data
    resp = await client.get(f"/api/v1/resumes/{resume['id']}/parsed")

    assert resp.status_code == 200
    body = resp.json()
    assert body["parsing_status"] == "completed"
    assert body["parsed_data"] is not None


async def test_get_parsed_resume_before_parsing(client):
    """GET /resumes/{id}/parsed before parsing returns pending status."""
    candidate = await _create_candidate(client)
    resume = await _upload_resume(client, candidate["id"])

    resp = await client.get(f"/api/v1/resumes/{resume['id']}/parsed")

    assert resp.status_code == 200
    body = resp.json()
    assert body["parsing_status"] == "pending"
    assert body["parsed_data"] is None
