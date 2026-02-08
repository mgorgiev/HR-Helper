import uuid

from fastapi import APIRouter, Depends, Query
from google import genai
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_llm_client, get_vector_store
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.schemas.match import CandidateMatch, JobMatch, MatchResults
from app.services import candidate_service, job_service, matching_service
from app.storage.vector_store import VectorStore

router = APIRouter(prefix="/matching", tags=["matching"])


@router.get("/jobs/{job_id}/candidates", response_model=MatchResults)
async def get_candidate_matches(
    job_id: uuid.UUID,
    limit: int = Query(default=10, le=50),
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
    llm_client: genai.Client = Depends(get_llm_client),
    vector_store: VectorStore = Depends(get_vector_store),
) -> MatchResults:
    """Get ranked candidates for a job with Gemini explanations."""
    job = await job_service.get_job(db, job_id)
    if not job:
        raise NotFoundError("Job", str(job_id))

    settings = get_settings()
    matches: list[CandidateMatch] = await matching_service.match_candidates_to_job(
        db=db,
        client=llm_client,
        vector_store=vector_store,
        job=job,
        model=settings.gemini_model,
        embedding_model=settings.gemini_embedding_model,
        limit=limit,
        min_score=min_score,
    )

    return MatchResults(job_id=job_id, matches=matches, total=len(matches))


@router.get("/candidates/{candidate_id}/jobs", response_model=MatchResults)
async def get_job_matches(
    candidate_id: uuid.UUID,
    limit: int = Query(default=10, le=50),
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
    llm_client: genai.Client = Depends(get_llm_client),
    vector_store: VectorStore = Depends(get_vector_store),
) -> MatchResults:
    """Get matching jobs for a candidate with Gemini explanations."""
    candidate = await candidate_service.get_candidate(db, candidate_id)
    if not candidate:
        raise NotFoundError("Candidate", str(candidate_id))

    settings = get_settings()
    matches: list[JobMatch] = await matching_service.match_jobs_to_candidate(
        db=db,
        client=llm_client,
        vector_store=vector_store,
        candidate_id=candidate_id,
        model=settings.gemini_model,
        embedding_model=settings.gemini_embedding_model,
        limit=limit,
        min_score=min_score,
    )

    return MatchResults(candidate_id=candidate_id, matches=matches, total=len(matches))
