import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import ConflictError, NotFoundError
from app.schemas import PaginatedResponse
from app.schemas.candidate import CandidateCreate, CandidateRead, CandidateUpdate
from app.services import candidate_service

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("/", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    data: CandidateCreate,
    db: AsyncSession = Depends(get_db),
) -> CandidateRead:
    try:
        candidate = await candidate_service.create_candidate(db, data)
    except IntegrityError as e:
        raise ConflictError(f"A candidate with email '{data.email}' already exists") from e
    return CandidateRead.model_validate(candidate)


@router.get("/", response_model=PaginatedResponse[CandidateRead])
async def list_candidates(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[CandidateRead]:
    items, total = await candidate_service.list_candidates(db, skip, limit, status_filter)
    return PaginatedResponse(
        items=[CandidateRead.model_validate(c) for c in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{candidate_id}", response_model=CandidateRead)
async def get_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CandidateRead:
    candidate = await candidate_service.get_candidate(db, candidate_id)
    if not candidate:
        raise NotFoundError("Candidate", str(candidate_id))
    return CandidateRead.model_validate(candidate)


@router.patch("/{candidate_id}", response_model=CandidateRead)
async def update_candidate(
    candidate_id: uuid.UUID,
    data: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
) -> CandidateRead:
    candidate = await candidate_service.get_candidate(db, candidate_id)
    if not candidate:
        raise NotFoundError("Candidate", str(candidate_id))
    try:
        updated = await candidate_service.update_candidate(db, candidate, data)
    except IntegrityError as e:
        raise ConflictError(f"A candidate with email '{data.email}' already exists") from e
    return CandidateRead.model_validate(updated)


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    candidate = await candidate_service.get_candidate(db, candidate_id)
    if not candidate:
        raise NotFoundError("Candidate", str(candidate_id))
    await candidate_service.delete_candidate(db, candidate)
