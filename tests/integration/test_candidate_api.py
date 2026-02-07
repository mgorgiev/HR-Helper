"""Integration tests for the candidates HTTP API.

These tests exercise the /api/v1/candidates endpoints through an HTTPX
AsyncClient wired to the FastAPI app with a real PostgreSQL database.
"""

import uuid

import pytest

from tests.conftest import make_candidate_payload

pytestmark = pytest.mark.integration

API = "/api/v1/candidates"


# ── helpers ──────────────────────────────────────────────────────────────


async def _create_candidate(client, **overrides):
    """POST a new candidate and return the parsed JSON response."""
    payload = make_candidate_payload(**overrides)
    resp = await client.post(API, json=payload)
    assert resp.status_code == 201
    return resp.json()


# ── tests ────────────────────────────────────────────────────────────────


async def test_post_candidate_201(client):
    """POST /candidates returns 201 with the created candidate body."""
    payload = make_candidate_payload(first_name="Jane", last_name="Doe")
    resp = await client.post(API, json=payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["first_name"] == "Jane"
    assert body["last_name"] == "Doe"
    assert body["email"] == payload["email"]
    assert body["status"] == "new"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


async def test_post_candidate_duplicate_email_409(client):
    """POST /candidates with a duplicate email returns 409 Conflict."""
    shared_email = f"dup.{uuid.uuid4().hex[:8]}@example.com"
    await _create_candidate(client, email=shared_email)

    payload = make_candidate_payload(email=shared_email)
    resp = await client.post(API, json=payload)

    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"].lower()


async def test_get_candidate_200(client):
    """GET /candidates/{id} returns the candidate."""
    created = await _create_candidate(client, first_name="GetMe")
    cid = created["id"]

    resp = await client.get(f"{API}/{cid}")

    assert resp.status_code == 200
    assert resp.json()["id"] == cid
    assert resp.json()["first_name"] == "GetMe"


async def test_get_candidate_404(client):
    """GET /candidates/{id} with a nonexistent UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"{API}/{fake_id}")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_list_candidates_200(client):
    """GET /candidates returns a paginated response."""
    await _create_candidate(client, first_name="ListA")
    await _create_candidate(client, first_name="ListB")

    resp = await client.get(API, params={"skip": 0, "limit": 10})

    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "skip" in body
    assert "limit" in body
    assert body["total"] >= 2
    assert len(body["items"]) >= 2


async def test_list_candidates_filter_status(client):
    """GET /candidates?status=new filters by status correctly."""
    await _create_candidate(client, status="new")
    await _create_candidate(client, status="screening")

    resp = await client.get(API, params={"status": "new"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert all(c["status"] == "new" for c in body["items"])


async def test_patch_candidate_200(client):
    """PATCH /candidates/{id} updates the specified fields."""
    created = await _create_candidate(client, first_name="Old", last_name="Name")
    cid = created["id"]

    resp = await client.patch(
        f"{API}/{cid}",
        json={"first_name": "New", "status": "interview"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["first_name"] == "New"
    assert body["last_name"] == "Name"  # unchanged
    assert body["status"] == "interview"


async def test_delete_candidate_204(client):
    """DELETE /candidates/{id} returns 204 and removes the resource."""
    created = await _create_candidate(client)
    cid = created["id"]

    resp = await client.delete(f"{API}/{cid}")
    assert resp.status_code == 204

    # Confirm it is gone
    get_resp = await client.get(f"{API}/{cid}")
    assert get_resp.status_code == 404
