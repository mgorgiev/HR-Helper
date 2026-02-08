"""Unit tests for match schemas."""

import uuid

import pytest

from app.schemas.match import CandidateMatch, JobMatch, MatchResults


@pytest.mark.unit
class TestCandidateMatch:
    def test_valid_candidate_match(self) -> None:
        m = CandidateMatch(
            candidate_id=uuid.uuid4(),
            resume_id=uuid.uuid4(),
            candidate_name="John Doe",
            score=0.85,
            explanation="Strong Python skills match the job requirements.",
        )
        assert m.candidate_name == "John Doe"
        assert m.score == 0.85


@pytest.mark.unit
class TestJobMatch:
    def test_valid_job_match(self) -> None:
        m = JobMatch(
            job_id=uuid.uuid4(),
            job_title="Backend Developer",
            score=0.92,
            explanation="Great fit for the role.",
        )
        assert m.job_title == "Backend Developer"
        assert m.score == 0.92


@pytest.mark.unit
class TestMatchResults:
    def test_match_results_with_candidate_matches(self) -> None:
        job_id = uuid.uuid4()
        matches = [
            CandidateMatch(
                candidate_id=uuid.uuid4(),
                resume_id=uuid.uuid4(),
                candidate_name="Alice",
                score=0.9,
                explanation="Excellent match.",
            ),
        ]
        result = MatchResults(job_id=job_id, matches=matches, total=1)
        assert result.job_id == job_id
        assert result.candidate_id is None
        assert result.total == 1
        assert len(result.matches) == 1

    def test_match_results_with_job_matches(self) -> None:
        cid = uuid.uuid4()
        matches = [
            JobMatch(
                job_id=uuid.uuid4(),
                job_title="Dev",
                score=0.8,
                explanation="Good match.",
            ),
        ]
        result = MatchResults(candidate_id=cid, matches=matches, total=1)
        assert result.candidate_id == cid
        assert result.job_id is None

    def test_match_results_empty(self) -> None:
        result = MatchResults(job_id=uuid.uuid4(), matches=[], total=0)
        assert result.total == 0
        assert result.matches == []
