import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.schemas.candidate import CandidateCreate, CandidateUpdate


async def create_candidate(db: AsyncSession, data: CandidateCreate) -> Candidate:
    candidate = Candidate(**data.model_dump())
    db.add(candidate)
    await db.flush()
    await db.refresh(candidate)
    return candidate


async def get_candidate(db: AsyncSession, candidate_id: uuid.UUID) -> Candidate | None:
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    return result.scalar_one_or_none()


async def list_candidates(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
) -> tuple[list[Candidate], int]:
    query = select(Candidate)
    count_query = select(func.count()).select_from(Candidate)

    if status:
        query = query.where(Candidate.status == status)
        count_query = count_query.where(Candidate.status == status)

    total = (await db.execute(count_query)).scalar_one()
    results = await db.execute(
        query.offset(skip).limit(limit).order_by(Candidate.created_at.desc())
    )
    return list(results.scalars().all()), total


async def update_candidate(
    db: AsyncSession, candidate: Candidate, data: CandidateUpdate
) -> Candidate:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(candidate, field, value)
    await db.flush()
    await db.refresh(candidate)
    return candidate


async def delete_candidate(db: AsyncSession, candidate: Candidate) -> None:
    await db.delete(candidate)
    await db.flush()
