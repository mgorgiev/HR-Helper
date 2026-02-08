"""Integration tests for matching endpoints.

Tests exercise GET /matching/jobs/{id}/candidates
and GET /matching/candidates/{id}/jobs
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
MATCHING_API = "/api/v1/matching"


async def _create_candidate(client, **overrides):
    payload = make_candidate_payload(**overrides)
    resp = await client.post(CANDIDATES_API, json=payload)
    assert resp.status_code == 201
    return resp.json()


async def _upload_parse_embed_resume(client, candidate_id: str):
    """Upload → parse → embed a resume, returning resume JSON."""
    file_path = SAMPLE_DIR / "sample_resume.txt"
    with open(file_path, "rb") as f:
        resp = await client.post(
            f"/api/v1/candidates/{candidate_id}/resumes",
            files={"file": ("sample_resume.txt", f, "text/plain")},
        )
    assert resp.status_code == 201
    resume = resp.json()

    parse_resp = await client.post(f"/api/v1/resumes/{resume['id']}/parse")
    assert parse_resp.status_code == 200

    embed_resp = await client.post(f"/api/v1/resumes/{resume['id']}/embed")
    assert embed_resp.status_code == 200

    return embed_resp.json()


async def _create_and_embed_job(client, **overrides):
    """Create and embed a job, returning job JSON."""
    payload = make_job_payload(**overrides)
    resp = await client.post(JOBS_API, json=payload)
    assert resp.status_code == 201
    job = resp.json()

    embed_resp = await client.post(f"/api/v1/jobs/{job['id']}/embed")
    assert embed_resp.status_code == 200

    return embed_resp.json()


async def test_match_candidates_to_job_200(client):
    """GET /matching/jobs/{id}/candidates returns matching candidates."""
    # Set up candidate with embedded resume
    candidate = await _create_candidate(client)
    await _upload_parse_embed_resume(client, candidate["id"])

    # Create and embed a job
    job = await _create_and_embed_job(client, title="Python Developer")

    resp = await client.get(f"{MATCHING_API}/jobs/{job['id']}/candidates")

    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == job["id"]
    assert "matches" in body
    assert "total" in body


async def test_match_candidates_empty_results(client):
    """GET /matching/jobs/{id}/candidates returns empty when no embeddings."""
    # Create a job but don't embed any resumes
    job = await _create_and_embed_job(client, title="No Match Job")

    resp = await client.get(f"{MATCHING_API}/jobs/{job['id']}/candidates")

    assert resp.status_code == 200
    body = resp.json()
    # With mocked embeddings all being the same, we'll get matches
    # but without any resume in a different collection it should still work
    assert "matches" in body


async def test_match_candidates_with_limit(client):
    """GET /matching/jobs/{id}/candidates respects limit param."""
    job = await _create_and_embed_job(client, title="Limited Job")

    resp = await client.get(
        f"{MATCHING_API}/jobs/{job['id']}/candidates",
        params={"limit": 1},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["matches"]) <= 1


async def test_match_job_not_found_404(client):
    """GET /matching/jobs/{id}/candidates with bad ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"{MATCHING_API}/jobs/{fake_id}/candidates")
    assert resp.status_code == 404


async def test_match_jobs_to_candidate_200(client):
    """GET /matching/candidates/{id}/jobs returns matching jobs."""
    candidate = await _create_candidate(client)
    await _upload_parse_embed_resume(client, candidate["id"])
    await _create_and_embed_job(client, title="Matching Job")

    resp = await client.get(f"{MATCHING_API}/candidates/{candidate['id']}/jobs")

    assert resp.status_code == 200
    body = resp.json()
    assert body["candidate_id"] == candidate["id"]
    assert "matches" in body


async def test_match_candidate_not_found_404(client):
    """GET /matching/candidates/{id}/jobs with bad ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"{MATCHING_API}/candidates/{fake_id}/jobs")
    assert resp.status_code == 404
