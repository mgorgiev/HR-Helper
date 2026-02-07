"""Integration tests for the job service layer.

These tests exercise job CRUD operations against a real PostgreSQL database
via an async SQLAlchemy session that is rolled back after every test.
"""

import uuid

import pytest

from app.schemas.job import JobCreate, JobUpdate
from app.services import job_service
from tests.conftest import make_job_payload

pytestmark = pytest.mark.integration


# ── helpers ──────────────────────────────────────────────────────────────


def _job_create(**overrides) -> JobCreate:
    return JobCreate(**make_job_payload(**overrides))


# ── tests ────────────────────────────────────────────────────────────────


async def test_create_job(db_session):
    """create_job returns a Job with UUID, defaults, and timestamps."""
    data = _job_create(title="Backend Developer")
    job = await job_service.create_job(db_session, data)

    assert job.id is not None
    assert isinstance(job.id, uuid.UUID)
    assert job.title == "Backend Developer"
    assert job.department == "Engineering"
    assert job.employment_type == "full_time"
    assert job.is_active is True
    assert job.created_at is not None
    assert job.updated_at is not None


async def test_get_job_found(db_session):
    """get_job returns the job when it exists."""
    data = _job_create()
    created = await job_service.create_job(db_session, data)

    fetched = await job_service.get_job(db_session, created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.title == created.title


async def test_get_job_not_found(db_session):
    """get_job returns None for a nonexistent UUID."""
    result = await job_service.get_job(db_session, uuid.uuid4())
    assert result is None


async def test_list_jobs_pagination(db_session):
    """list_jobs respects skip and limit parameters."""
    for i in range(4):
        await job_service.create_job(db_session, _job_create(title=f"Role {i}"))

    page1, total = await job_service.list_jobs(db_session, skip=0, limit=2)
    assert len(page1) == 2
    assert total == 4

    page2, _ = await job_service.list_jobs(db_session, skip=2, limit=2)
    assert len(page2) == 2

    page1_ids = {j.id for j in page1}
    page2_ids = {j.id for j in page2}
    assert page1_ids.isdisjoint(page2_ids)


async def test_list_jobs_active_only(db_session):
    """list_jobs filters correctly by is_active flag."""
    await job_service.create_job(db_session, _job_create(title="Active Job", is_active=True))
    await job_service.create_job(db_session, _job_create(title="Closed Job", is_active=False))

    active_items, active_total = await job_service.list_jobs(db_session, is_active=True)
    assert active_total >= 1
    assert all(j.is_active for j in active_items)

    inactive_items, inactive_total = await job_service.list_jobs(db_session, is_active=False)
    assert inactive_total >= 1
    assert all(not j.is_active for j in inactive_items)


async def test_update_job(db_session):
    """update_job modifies only the specified fields."""
    data = _job_create(title="Original Title", department="Engineering")
    job = await job_service.create_job(db_session, data)

    update_data = JobUpdate(title="Updated Title")
    updated = await job_service.update_job(db_session, job, update_data)

    assert updated.title == "Updated Title"
    assert updated.department == "Engineering"  # unchanged


async def test_delete_job(db_session):
    """delete_job removes the record from the database."""
    data = _job_create()
    job = await job_service.create_job(db_session, data)
    jid = job.id

    await job_service.delete_job(db_session, job)

    assert await job_service.get_job(db_session, jid) is None
