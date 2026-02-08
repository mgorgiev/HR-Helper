"""End-to-end AI workflow tests.

These tests exercise the full intelligence pipeline:
upload → extract → parse → embed → match.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke

SAMPLE_DIR = Path(__file__).parent.parent.parent / "sample_data" / "resumes"
CANDIDATES_API = "/api/v1/candidates"
JOBS_API = "/api/v1/jobs"
MATCHING_API = "/api/v1/matching"


async def test_full_resume_intelligence_pipeline(client):
    """Upload resume → extract → parse → embed → verify all fields set."""
    # 1. Create candidate
    resp = await client.post(
        CANDIDATES_API,
        json={
            "first_name": "AI",
            "last_name": "Pipeline",
            "email": "ai.pipeline.smoke@example.com",
        },
    )
    assert resp.status_code == 201
    candidate = resp.json()
    candidate_id = candidate["id"]

    # 2. Upload resume
    with open(SAMPLE_DIR / "sample_resume.txt", "rb") as f:
        resp = await client.post(
            f"/api/v1/candidates/{candidate_id}/resumes",
            files={"file": ("resume.txt", f, "text/plain")},
        )
    assert resp.status_code == 201
    resume = resp.json()
    resume_id = resume["id"]
    assert resume["extraction_status"] == "completed"
    assert resume["extracted_text"] is not None

    # 3. Parse
    resp = await client.post(f"/api/v1/resumes/{resume_id}/parse")
    assert resp.status_code == 200
    parsed = resp.json()
    assert parsed["parsing_status"] == "completed"
    assert parsed["parsed_data"] is not None
    assert parsed["parsed_data"]["full_name"] is not None

    # 4. Embed
    resp = await client.post(f"/api/v1/resumes/{resume_id}/embed")
    assert resp.status_code == 200

    # 5. Verify final state
    resp = await client.get(f"/api/v1/resumes/{resume_id}")
    assert resp.status_code == 200
    final = resp.json()
    assert final["extraction_status"] == "completed"
    assert final["parsing_status"] == "completed"
    assert final["parsed_data"] is not None

    # Cleanup
    await client.delete(f"/api/v1/candidates/{candidate_id}")


async def test_candidate_job_matching(client):
    """Create candidate + resume + job → parse → embed → match."""
    # 1. Create candidate
    resp = await client.post(
        CANDIDATES_API,
        json={
            "first_name": "Match",
            "last_name": "Test",
            "email": "match.test.smoke@example.com",
        },
    )
    assert resp.status_code == 201
    candidate = resp.json()

    # 2. Upload and process resume
    with open(SAMPLE_DIR / "sample_resume.txt", "rb") as f:
        resp = await client.post(
            f"/api/v1/candidates/{candidate['id']}/resumes",
            files={"file": ("resume.txt", f, "text/plain")},
        )
    assert resp.status_code == 201
    resume = resp.json()

    # Parse and embed resume
    resp = await client.post(f"/api/v1/resumes/{resume['id']}/parse")
    assert resp.status_code == 200
    resp = await client.post(f"/api/v1/resumes/{resume['id']}/embed")
    assert resp.status_code == 200

    # 3. Create and embed job
    resp = await client.post(
        JOBS_API,
        json={
            "title": "Python Developer",
            "description": "Build APIs with FastAPI",
            "requirements": "Python, FastAPI, SQL, REST",
        },
    )
    assert resp.status_code == 201
    job = resp.json()
    resp = await client.post(f"/api/v1/jobs/{job['id']}/embed")
    assert resp.status_code == 200

    # 4. Match candidates to job
    resp = await client.get(f"{MATCHING_API}/jobs/{job['id']}/candidates")
    assert resp.status_code == 200
    results = resp.json()
    assert results["job_id"] == job["id"]
    assert isinstance(results["matches"], list)
    assert results["total"] >= 0

    # 5. Match jobs to candidate
    resp = await client.get(f"{MATCHING_API}/candidates/{candidate['id']}/jobs")
    assert resp.status_code == 200
    results = resp.json()
    assert results["candidate_id"] == candidate["id"]
    assert isinstance(results["matches"], list)

    # Cleanup
    await client.delete(f"/api/v1/candidates/{candidate['id']}")
    await client.delete(f"/api/v1/jobs/{job['id']}")
