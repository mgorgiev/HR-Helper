"""Unit tests for Pydantic schema validation."""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas import PaginatedResponse
from app.schemas.candidate import (
    CandidateCreate,
    CandidateRead,
    CandidateStatus,
    CandidateUpdate,
)
from app.schemas.job import EmploymentType, JobCreate, JobUpdate
from app.schemas.resume import ResumeRead


@pytest.mark.unit
class TestCandidateCreate:
    def test_candidate_create_valid(self) -> None:
        """A valid input should pass validation."""
        candidate = CandidateCreate(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            phone="+1234567890",
            status=CandidateStatus.NEW,
            notes="Great candidate",
        )
        assert candidate.first_name == "Jane"
        assert candidate.last_name == "Smith"
        assert candidate.email == "jane.smith@example.com"
        assert candidate.phone == "+1234567890"
        assert candidate.status == CandidateStatus.NEW
        assert candidate.notes == "Great candidate"

    def test_candidate_create_missing_email(self) -> None:
        """Omitting the required email field should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CandidateCreate(
                first_name="Jane",
                last_name="Smith",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("email",) for e in errors)

    def test_candidate_create_invalid_email(self) -> None:
        """A malformed email should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CandidateCreate(
                first_name="Jane",
                last_name="Smith",
                email="not-an-email",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("email",) for e in errors)


@pytest.mark.unit
class TestCandidateUpdate:
    def test_candidate_update_partial(self) -> None:
        """Only provided fields should be set; others remain None."""
        update = CandidateUpdate(first_name="Updated")
        assert update.first_name == "Updated"
        assert update.last_name is None
        assert update.email is None
        assert update.phone is None
        assert update.status is None
        assert update.notes is None


@pytest.mark.unit
class TestCandidateStatus:
    def test_candidate_status_enum_values(self) -> None:
        """All valid statuses should be accepted; an invalid one should fail."""
        valid_statuses = ["new", "screening", "interview", "offer", "hired", "rejected"]
        for status_val in valid_statuses:
            candidate = CandidateCreate(
                first_name="A",
                last_name="B",
                email="ab@example.com",
                status=status_val,
            )
            assert candidate.status == status_val

        with pytest.raises(ValidationError):
            CandidateCreate(
                first_name="A",
                last_name="B",
                email="ab@example.com",
                status="nonexistent_status",
            )


@pytest.mark.unit
class TestJobCreate:
    def test_job_create_valid(self) -> None:
        """A valid job input should pass validation."""
        job = JobCreate(
            title="Backend Developer",
            department="Engineering",
            description="Build APIs",
            requirements="Python, SQL",
            location="Remote",
            employment_type=EmploymentType.FULL_TIME,
            is_active=True,
        )
        assert job.title == "Backend Developer"
        assert job.department == "Engineering"
        assert job.employment_type == EmploymentType.FULL_TIME
        assert job.is_active is True

    def test_job_create_defaults(self) -> None:
        """employment_type should default to full_time, is_active to True."""
        job = JobCreate(title="Designer")
        assert job.employment_type == EmploymentType.FULL_TIME
        assert job.is_active is True


@pytest.mark.unit
class TestJobUpdate:
    def test_job_update_all_optional(self) -> None:
        """An empty dict (no fields) should be valid for JobUpdate."""
        update = JobUpdate()
        assert update.title is None
        assert update.department is None
        assert update.description is None
        assert update.requirements is None
        assert update.location is None
        assert update.employment_type is None
        assert update.is_active is None


@pytest.mark.unit
class TestResumeRead:
    def test_resume_read_from_attributes(self) -> None:
        """from_attributes should work with a mock object (SimpleNamespace)."""
        now = datetime.now(tz=UTC)
        resume_id = uuid.uuid4()
        candidate_id = uuid.uuid4()

        mock_obj = SimpleNamespace(
            id=resume_id,
            candidate_id=candidate_id,
            original_filename="resume.pdf",
            stored_filename="abc123.pdf",
            file_path="uploads/abc123.pdf",
            content_type="application/pdf",
            file_size_bytes=102400,
            extracted_text="Some extracted text",
            extraction_status="completed",
            extraction_error=None,
            created_at=now,
            updated_at=now,
        )

        resume = ResumeRead.model_validate(mock_obj, from_attributes=True)
        assert resume.id == resume_id
        assert resume.candidate_id == candidate_id
        assert resume.original_filename == "resume.pdf"
        assert resume.extracted_text == "Some extracted text"
        assert resume.extraction_status == "completed"


@pytest.mark.unit
class TestPaginatedResponse:
    def test_paginated_response_generic(self) -> None:
        """PaginatedResponse[CandidateRead] should serialize correctly."""
        now = datetime.now(tz=UTC)
        candidate_id = uuid.uuid4()

        candidate_data = CandidateRead(
            id=candidate_id,
            first_name="Alice",
            last_name="Wonder",
            email="alice@example.com",
            phone=None,
            status="new",
            notes=None,
            created_at=now,
            updated_at=now,
        )

        paginated = PaginatedResponse[CandidateRead](
            items=[candidate_data],
            total=1,
            skip=0,
            limit=10,
        )

        assert paginated.total == 1
        assert paginated.skip == 0
        assert paginated.limit == 10
        assert len(paginated.items) == 1
        assert paginated.items[0].id == candidate_id
        assert paginated.items[0].first_name == "Alice"

        # Verify serialization round-trip
        dumped = paginated.model_dump()
        assert dumped["total"] == 1
        assert len(dumped["items"]) == 1
        assert dumped["items"][0]["first_name"] == "Alice"
