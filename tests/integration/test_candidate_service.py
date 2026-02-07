"""Integration tests for the candidate service layer.

These tests exercise candidate CRUD operations against a real PostgreSQL
database via an async SQLAlchemy session that is rolled back after every test.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.schemas.candidate import CandidateCreate, CandidateUpdate
from app.services import candidate_service
from tests.conftest import make_candidate_payload

pytestmark = pytest.mark.integration


# ── helpers ──────────────────────────────────────────────────────────────


def _candidate_create(**overrides) -> CandidateCreate:
    return CandidateCreate(**make_candidate_payload(**overrides))


# ── tests ────────────────────────────────────────────────────────────────


async def test_create_candidate(db_session):
    """create_candidate returns a Candidate with a UUID id and timestamps."""
    data = _candidate_create(first_name="Alice", last_name="Smith")
    candidate = await candidate_service.create_candidate(db_session, data)

    assert candidate.id is not None
    assert isinstance(candidate.id, uuid.UUID)
    assert candidate.first_name == "Alice"
    assert candidate.last_name == "Smith"
    assert candidate.email == data.email
    assert candidate.status == "new"
    assert candidate.created_at is not None
    assert candidate.updated_at is not None


async def test_get_candidate_found(db_session):
    """get_candidate returns the candidate when it exists."""
    data = _candidate_create()
    created = await candidate_service.create_candidate(db_session, data)

    fetched = await candidate_service.get_candidate(db_session, created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.email == created.email


async def test_get_candidate_not_found(db_session):
    """get_candidate returns None for a nonexistent UUID."""
    result = await candidate_service.get_candidate(db_session, uuid.uuid4())
    assert result is None


async def test_list_candidates_empty(db_session):
    """list_candidates on an empty table returns ([], 0)."""
    items, total = await candidate_service.list_candidates(db_session)
    assert items == []
    assert total == 0


async def test_list_candidates_pagination(db_session):
    """list_candidates respects skip and limit parameters."""
    for i in range(5):
        await candidate_service.create_candidate(
            db_session, _candidate_create(first_name=f"Page{i}")
        )

    # First page
    page1, total = await candidate_service.list_candidates(db_session, skip=0, limit=2)
    assert len(page1) == 2
    assert total == 5

    # Second page
    page2, _ = await candidate_service.list_candidates(db_session, skip=2, limit=2)
    assert len(page2) == 2

    # Ensure no overlap between pages
    page1_ids = {c.id for c in page1}
    page2_ids = {c.id for c in page2}
    assert page1_ids.isdisjoint(page2_ids)


async def test_list_candidates_filter_by_status(db_session):
    """list_candidates filters correctly by status."""
    await candidate_service.create_candidate(db_session, _candidate_create(status="new"))
    await candidate_service.create_candidate(db_session, _candidate_create(status="screening"))
    await candidate_service.create_candidate(db_session, _candidate_create(status="screening"))

    items, total = await candidate_service.list_candidates(db_session, status="screening")
    assert total == 2
    assert len(items) == 2
    assert all(c.status == "screening" for c in items)


async def test_update_candidate_partial(db_session):
    """update_candidate only modifies the fields that are explicitly set."""
    data = _candidate_create(first_name="Before", last_name="Update")
    candidate = await candidate_service.create_candidate(db_session, data)

    original_email = candidate.email
    update_data = CandidateUpdate(first_name="After")
    updated = await candidate_service.update_candidate(db_session, candidate, update_data)

    assert updated.first_name == "After"
    assert updated.last_name == "Update"  # unchanged
    assert updated.email == original_email  # unchanged


async def test_delete_candidate(db_session):
    """delete_candidate removes the record from the database."""
    data = _candidate_create()
    candidate = await candidate_service.create_candidate(db_session, data)
    cid = candidate.id

    await candidate_service.delete_candidate(db_session, candidate)

    assert await candidate_service.get_candidate(db_session, cid) is None


async def test_create_duplicate_email_raises(db_session):
    """Creating a second candidate with the same email raises IntegrityError."""
    shared_email = f"dup.{uuid.uuid4().hex[:8]}@example.com"
    await candidate_service.create_candidate(db_session, _candidate_create(email=shared_email))

    with pytest.raises(IntegrityError):
        await candidate_service.create_candidate(db_session, _candidate_create(email=shared_email))
