"""Integration tests for the jobs HTTP API.

These tests exercise the /api/v1/jobs endpoints through an HTTPX AsyncClient
wired to the FastAPI app with a real PostgreSQL database.
"""

import uuid

import pytest

from tests.conftest import make_job_payload

pytestmark = pytest.mark.integration

API = "/api/v1/jobs"


# ── helpers ──────────────────────────────────────────────────────────────


async def _create_job(client, **overrides):
    """POST a new job and return the parsed JSON response."""
    payload = make_job_payload(**overrides)
    resp = await client.post(API, json=payload)
    assert resp.status_code == 201
    return resp.json()


# ── tests ────────────────────────────────────────────────────────────────


async def test_post_job_201(client):
    """POST /jobs returns 201 with the created job body."""
    payload = make_job_payload(title="Data Engineer", department="Data")
    resp = await client.post(API, json=payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Data Engineer"
    assert body["department"] == "Data"
    assert body["employment_type"] == "full_time"
    assert body["is_active"] is True
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


async def test_get_job_200(client):
    """GET /jobs/{id} returns the job."""
    created = await _create_job(client, title="GetThisJob")
    jid = created["id"]

    resp = await client.get(f"{API}/{jid}")

    assert resp.status_code == 200
    assert resp.json()["id"] == jid
    assert resp.json()["title"] == "GetThisJob"


async def test_get_job_404(client):
    """GET /jobs/{id} with a nonexistent UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"{API}/{fake_id}")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_list_jobs_200(client):
    """GET /jobs returns a paginated response."""
    await _create_job(client, title="Job A")
    await _create_job(client, title="Job B")

    resp = await client.get(API, params={"skip": 0, "limit": 10})

    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 2
    assert len(body["items"]) >= 2


async def test_list_jobs_filter_active(client):
    """GET /jobs?is_active=true returns only active jobs."""
    await _create_job(client, title="Active Role", is_active=True)
    await _create_job(client, title="Closed Role", is_active=False)

    resp = await client.get(API, params={"is_active": "true"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert all(j["is_active"] is True for j in body["items"])


async def test_patch_job_200(client):
    """PATCH /jobs/{id} updates the specified fields."""
    created = await _create_job(client, title="Old Title", department="Eng")
    jid = created["id"]

    resp = await client.patch(
        f"{API}/{jid}",
        json={"title": "New Title", "is_active": False},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "New Title"
    assert body["department"] == "Eng"  # unchanged
    assert body["is_active"] is False


async def test_delete_job_204(client):
    """DELETE /jobs/{id} returns 204 and removes the resource."""
    created = await _create_job(client)
    jid = created["id"]

    resp = await client.delete(f"{API}/{jid}")
    assert resp.status_code == 204

    # Confirm it is gone
    get_resp = await client.get(f"{API}/{jid}")
    assert get_resp.status_code == 404
