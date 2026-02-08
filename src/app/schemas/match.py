import uuid

from pydantic import BaseModel


class CandidateMatch(BaseModel):
    candidate_id: uuid.UUID
    resume_id: uuid.UUID
    candidate_name: str
    score: float
    explanation: str


class JobMatch(BaseModel):
    job_id: uuid.UUID
    job_title: str
    score: float
    explanation: str


class MatchResults(BaseModel):
    job_id: uuid.UUID | None = None
    candidate_id: uuid.UUID | None = None
    matches: list[CandidateMatch] | list[JobMatch]
    total: int
