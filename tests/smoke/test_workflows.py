"""End-to-end workflow tests that exercise multi-step scenarios."""

from pathlib import Path

import pytest

SAMPLE_DIR = Path(__file__).parent.parent.parent / "sample_data" / "resumes"

pytestmark = pytest.mark.smoke


async def test_full_candidate_lifecycle(client):
    """Create candidate → upload resume → extract → update status → filter → delete cascade."""
    # 1. Create candidate
    resp = await client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Smoke",
            "last_name": "Test",
            "email": "smoke.test.lifecycle@example.com",
        },
    )
    assert resp.status_code == 201
    candidate = resp.json()
    candidate_id = candidate["id"]

    # 2. Upload PDF resume
    with open(SAMPLE_DIR / "sample_resume.pdf", "rb") as f:
        resp = await client.post(
            f"/api/v1/candidates/{candidate_id}/resumes",
            files={"file": ("resume.pdf", f, "application/pdf")},
        )
    assert resp.status_code == 201
    resume = resp.json()
    resume_id = resume["id"]
    assert resume["extraction_status"] in ("completed", "failed")

    # 3. Get extracted text
    resp = await client.get(f"/api/v1/resumes/{resume_id}/text")
    assert resp.status_code == 200
    text_data = resp.json()
    assert text_data["extraction_status"] == "completed"
    assert text_data["extracted_text"] is not None
    assert len(text_data["extracted_text"]) > 0

    # 4. Update candidate status to screening
    resp = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        json={"status": "screening"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "screening"

    # 5. Filter candidates by status
    resp = await client.get("/api/v1/candidates", params={"status": "screening"})
    assert resp.status_code == 200
    data = resp.json()
    ids = [c["id"] for c in data["items"]]
    assert candidate_id in ids

    # 6. Delete candidate — should cascade delete resume
    resp = await client.delete(f"/api/v1/candidates/{candidate_id}")
    assert resp.status_code == 204

    # 7. Verify resume is also gone (cascade)
    resp = await client.get(f"/api/v1/resumes/{resume_id}")
    assert resp.status_code == 404


async def test_full_job_lifecycle(client):
    """Create job → list → deactivate → filter → delete."""
    # 1. Create job
    resp = await client.post(
        "/api/v1/jobs",
        json={
            "title": "Smoke Test Engineer",
            "department": "QA",
            "description": "Run smoke tests all day",
            "location": "Remote",
        },
    )
    assert resp.status_code == 201
    job = resp.json()
    job_id = job["id"]

    # 2. List jobs — should appear
    resp = await client.get("/api/v1/jobs")
    assert resp.status_code == 200
    ids = [j["id"] for j in resp.json()["items"]]
    assert job_id in ids

    # 3. Deactivate
    resp = await client.patch(f"/api/v1/jobs/{job_id}", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # 4. Filter active only — should NOT appear
    resp = await client.get("/api/v1/jobs", params={"is_active": True})
    assert resp.status_code == 200
    ids = [j["id"] for j in resp.json()["items"]]
    assert job_id not in ids

    # 5. Delete
    resp = await client.delete(f"/api/v1/jobs/{job_id}")
    assert resp.status_code == 204

    # 6. Confirm gone
    resp = await client.get(f"/api/v1/jobs/{job_id}")
    assert resp.status_code == 404


async def test_multi_resume_per_candidate(client):
    """Create candidate → upload 3 resumes (PDF, DOCX, TXT) → list → delete one → list again."""
    # 1. Create candidate
    resp = await client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Multi",
            "last_name": "Resume",
            "email": "multi.resume.smoke@example.com",
        },
    )
    assert resp.status_code == 201
    candidate_id = resp.json()["id"]

    # 2. Upload 3 resumes
    resume_ids = []
    files_to_upload = [
        ("sample_resume.pdf", "application/pdf"),
        (
            "sample_resume.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        ("sample_resume.txt", "text/plain"),
    ]
    for filename, content_type in files_to_upload:
        with open(SAMPLE_DIR / filename, "rb") as f:
            resp = await client.post(
                f"/api/v1/candidates/{candidate_id}/resumes",
                files={"file": (filename, f, content_type)},
            )
        assert resp.status_code == 201
        resume_ids.append(resp.json()["id"])

    # 3. List resumes — should have 3
    resp = await client.get(f"/api/v1/candidates/{candidate_id}/resumes")
    assert resp.status_code == 200
    resumes = resp.json()
    assert len(resumes) == 3

    # 4. Verify each has extracted text
    for r in resumes:
        assert r["extraction_status"] == "completed"
        assert r["extracted_text"] is not None

    # 5. Delete one resume
    resp = await client.delete(f"/api/v1/resumes/{resume_ids[0]}")
    assert resp.status_code == 204

    # 6. List again — should have 2
    resp = await client.get(f"/api/v1/candidates/{candidate_id}/resumes")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # Cleanup
    await client.delete(f"/api/v1/candidates/{candidate_id}")


async def test_health_check_with_live_db(client):
    """Verify health and status endpoints work end-to-end."""
    # Health check
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "version" in data

    # Liveness check
    resp = await client.get("/api/v1/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
