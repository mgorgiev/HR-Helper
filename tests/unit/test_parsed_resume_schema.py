"""Unit tests for parsed resume schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.parsed_resume import Education, ParsedResumeData, WorkExperience


@pytest.mark.unit
class TestWorkExperience:
    def test_valid_work_experience(self) -> None:
        exp = WorkExperience(
            company="Acme Corp",
            title="Software Engineer",
            start_date="2020-01",
            end_date="2023-06",
            description="Built APIs",
        )
        assert exp.company == "Acme Corp"
        assert exp.title == "Software Engineer"
        assert exp.start_date == "2020-01"

    def test_work_experience_minimal(self) -> None:
        exp = WorkExperience(company="Acme", title="Dev")
        assert exp.company == "Acme"
        assert exp.start_date is None
        assert exp.end_date is None
        assert exp.description is None

    def test_work_experience_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            WorkExperience(company="Acme")  # missing title


@pytest.mark.unit
class TestEducation:
    def test_valid_education(self) -> None:
        edu = Education(
            institution="MIT",
            degree="BS",
            field="Computer Science",
            year="2020",
        )
        assert edu.institution == "MIT"
        assert edu.degree == "BS"
        assert edu.field == "Computer Science"

    def test_education_minimal(self) -> None:
        edu = Education(institution="State University")
        assert edu.institution == "State University"
        assert edu.degree is None
        assert edu.field is None
        assert edu.year is None

    def test_education_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            Education()  # missing institution


@pytest.mark.unit
class TestParsedResumeData:
    def test_full_parsed_resume(self) -> None:
        data = ParsedResumeData(
            full_name="John Doe",
            email="john@example.com",
            phone="+1234567890",
            summary="Experienced developer",
            skills=["Python", "FastAPI", "SQL"],
            experience=[
                WorkExperience(company="Acme", title="Dev"),
            ],
            education=[
                Education(institution="MIT", degree="BS"),
            ],
            languages=["English", "Spanish"],
            certifications=["AWS"],
        )
        assert data.full_name == "John Doe"
        assert len(data.skills) == 3
        assert len(data.experience) == 1
        assert len(data.education) == 1
        assert len(data.languages) == 2
        assert len(data.certifications) == 1

    def test_parsed_resume_defaults(self) -> None:
        data = ParsedResumeData()
        assert data.full_name is None
        assert data.email is None
        assert data.phone is None
        assert data.summary is None
        assert data.skills == []
        assert data.experience == []
        assert data.education == []
        assert data.languages == []
        assert data.certifications == []

    def test_parsed_resume_serialization(self) -> None:
        data = ParsedResumeData(
            full_name="Jane",
            skills=["Python"],
        )
        dumped = data.model_dump()
        assert dumped["full_name"] == "Jane"
        assert dumped["skills"] == ["Python"]
        assert dumped["experience"] == []
