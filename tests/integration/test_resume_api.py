"""Integration tests for the resumes HTTP API.

These tests exercise resume upload, retrieval, text extraction, download,
and deletion endpoints through an HTTPX AsyncClient wired to the FastAPI app
with a real PostgreSQL database and local file storage backed by a temp dir.
"""

import uuid
from pathlib import Path

import pytest

from tests.conftest import make_candidate_payload

pytestmark = pytest.mark.integration

SAMPLE_DIR = Path(__file__).parent.parent.parent / "sample_data" / "resumes"

CANDIDATES_API = "/api/v1/candidates"


# ── helpers ──────────────────────────────────────────────────────────────


async def _create_candidate(client, **overrides):
    """Create a candidate via the API and return its JSON body."""
    payload = make_candidate_payload(**overrides)
    resp = await client.post(CANDIDATES_API, json=payload)
    assert resp.status_code == 201
    return resp.json()


async def _upload_resume(client, candidate_id: str, filename: str, content_type: str):
    """Upload a sample file and return the response object."""
    file_path = SAMPLE_DIR / filename
    with open(file_path, "rb") as f:
        resp = await client.post(
            f"/api/v1/candidates/{candidate_id}/resumes",
            files={"file": (filename, f, content_type)},
        )
    return resp


# ── upload tests ─────────────────────────────────────────────────────────


async def test_upload_resume_pdf_201(client):
    """Uploading a PDF resume returns 201 with resume metadata."""
    candidate = await _create_candidate(client)
    resp = await _upload_resume(client, candidate["id"], "sample_resume.pdf", "application/pdf")

    assert resp.status_code == 201
    body = resp.json()
    assert body["original_filename"] == "sample_resume.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["candidate_id"] == candidate["id"]
    assert "id" in body
    assert body["file_size_bytes"] > 0


async def test_upload_resume_docx_201(client):
    """Uploading a DOCX resume returns 201."""
    candidate = await _create_candidate(client)
    resp = await _upload_resume(
        client,
        candidate["id"],
        "sample_resume.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["original_filename"] == "sample_resume.docx"
    assert body["candidate_id"] == candidate["id"]


async def test_upload_resume_txt_201(client):
    """Uploading a TXT resume returns 201."""
    candidate = await _create_candidate(client)
    resp = await _upload_resume(client, candidate["id"], "sample_resume.txt", "text/plain")

    assert resp.status_code == 201
    body = resp.json()
    assert body["original_filename"] == "sample_resume.txt"
    assert body["candidate_id"] == candidate["id"]


async def test_upload_resume_invalid_extension_422(client):
    """Uploading a file with a disallowed extension returns 422."""
    candidate = await _create_candidate(client)

    # Create a tiny fake .exe payload in-memory
    resp = await client.post(
        f"/api/v1/candidates/{candidate['id']}/resumes",
        files={"file": ("malware.exe", b"MZ fake content", "application/octet-stream")},
    )

    assert resp.status_code == 422
    assert "not allowed" in resp.json()["detail"].lower()


async def test_upload_resume_nonexistent_candidate_404(client):
    """Uploading a resume for a nonexistent candidate returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await _upload_resume(client, fake_id, "sample_resume.txt", "text/plain")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ── retrieval tests ──────────────────────────────────────────────────────


async def test_get_resume_200(client):
    """GET /resumes/{id} returns the resume metadata."""
    candidate = await _create_candidate(client)
    upload_resp = await _upload_resume(client, candidate["id"], "sample_resume.txt", "text/plain")
    resume_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/v1/resumes/{resume_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == resume_id
    assert body["original_filename"] == "sample_resume.txt"


async def test_get_extracted_text(client):
    """GET /resumes/{id}/text returns the extracted text payload."""
    candidate = await _create_candidate(client)
    upload_resp = await _upload_resume(client, candidate["id"], "sample_resume.txt", "text/plain")
    resume_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/v1/resumes/{resume_id}/text")

    assert resp.status_code == 200
    body = resp.json()
    assert "id" in body
    assert "extraction_status" in body
    assert "extracted_text" in body
    # For a .txt file, extraction should succeed
    assert body["extraction_status"] in ("completed", "pending")


async def test_download_resume(client):
    """GET /resumes/{id}/download returns the file content."""
    candidate = await _create_candidate(client)
    upload_resp = await _upload_resume(client, candidate["id"], "sample_resume.txt", "text/plain")
    resume_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/v1/resumes/{resume_id}/download")

    assert resp.status_code == 200
    # The response should contain file content
    assert len(resp.content) > 0


async def test_re_extract_resume(client):
    """POST /resumes/{id}/extract re-runs text extraction."""
    candidate = await _create_candidate(client)
    upload_resp = await _upload_resume(client, candidate["id"], "sample_resume.txt", "text/plain")
    resume_id = upload_resp.json()["id"]

    resp = await client.post(f"/api/v1/resumes/{resume_id}/extract")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == resume_id
    assert body["extraction_status"] in ("completed", "failed")


# ── deletion tests ───────────────────────────────────────────────────────


async def test_delete_resume_204(client):
    """DELETE /resumes/{id} returns 204 and removes the resource."""
    candidate = await _create_candidate(client)
    upload_resp = await _upload_resume(client, candidate["id"], "sample_resume.txt", "text/plain")
    resume_id = upload_resp.json()["id"]

    resp = await client.delete(f"/api/v1/resumes/{resume_id}")
    assert resp.status_code == 204

    # Confirm it is gone
    get_resp = await client.get(f"/api/v1/resumes/{resume_id}")
    assert get_resp.status_code == 404
