"""Integration tests for embedding endpoints.

Tests exercise POST /resumes/{id}/embed and POST /jobs/{id}/embed
with mocked Gemini and in-memory vector store.
"""

import uuid
from pathlib import Path

import pytest

from tests.conftest import make_candidate_payload, make_job_payload

pytestmark = pytest.mark.integration

SAMPLE_DIR = Path(__file__).parent.parent.parent / "sample_data" / "resumes"
CANDIDATES_API = "/api/v1/candidates"
JOBS_API = "/api/v1/jobs"


async def _create_candidate(client, **overrides):
    payload = make_candidate_payload(**overrides)
    resp = await client.post(CANDIDATES_API, json=payload)
    assert resp.status_code == 201
    return resp.json()


async def _upload_and_parse_resume(client, candidate_id: str):
    """Upload a resume and parse it, returning the resume JSON."""
    file_path = SAMPLE_DIR / "sample_resume.txt"
    with open(file_path, "rb") as f:
        resp = await client.post(
            f"/api/v1/candidates/{candidate_id}/resumes",
            files={"file": ("sample_resume.txt", f, "text/plain")},
        )
    assert resp.status_code == 201
    resume = resp.json()

    # Parse
    parse_resp = await client.post(f"/api/v1/resumes/{resume['id']}/parse")
    assert parse_resp.status_code == 200
    return parse_resp.json()


async def test_embed_resume_200(client):
    """POST /resumes/{id}/embed generates and stores embedding."""
    candidate = await _create_candidate(client)
    resume = await _upload_and_parse_resume(client, candidate["id"])

    resp = await client.post(f"/api/v1/resumes/{resume['id']}/embed")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == resume["id"]


async def test_embed_resume_not_parsed_422(client):
    """POST /resumes/{id}/embed without parsed data returns 422."""
    candidate = await _create_candidate(client)
    file_path = SAMPLE_DIR / "sample_resume.txt"
    with open(file_path, "rb") as f:
        resp = await client.post(
            f"/api/v1/candidates/{candidate['id']}/resumes",
            files={"file": ("sample_resume.txt", f, "text/plain")},
        )
    assert resp.status_code == 201
    resume = resp.json()

    # Try to embed without parsing first
    resp = await client.post(f"/api/v1/resumes/{resume['id']}/embed")
    assert resp.status_code == 422
    assert "parsed data" in resp.json()["detail"].lower()


async def test_embed_resume_not_found_404(client):
    """POST /resumes/{id}/embed with invalid ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(f"/api/v1/resumes/{fake_id}/embed")
    assert resp.status_code == 404


async def test_embed_job_200(client):
    """POST /jobs/{id}/embed generates and stores embedding."""
    payload = make_job_payload(title="Embedding Test Job")
    resp = await client.post(JOBS_API, json=payload)
    assert resp.status_code == 201
    job = resp.json()

    resp = await client.post(f"/api/v1/jobs/{job['id']}/embed")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == job["id"]


async def test_embed_job_not_found_404(client):
    """POST /jobs/{id}/embed with invalid ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(f"/api/v1/jobs/{fake_id}/embed")
    assert resp.status_code == 404
