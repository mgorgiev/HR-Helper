import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import NotFoundError
from app.schemas import PaginatedResponse
from app.schemas.job import JobCreate, JobRead, JobUpdate
from app.services import job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    data: JobCreate,
    db: AsyncSession = Depends(get_db),
) -> JobRead:
    job = await job_service.create_job(db, data)
    return JobRead.model_validate(job)


@router.get("/", response_model=PaginatedResponse[JobRead])
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[JobRead]:
    items, total = await job_service.list_jobs(db, skip, limit, is_active)
    return PaginatedResponse(
        items=[JobRead.model_validate(j) for j in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> JobRead:
    job = await job_service.get_job(db, job_id)
    if not job:
        raise NotFoundError("Job", str(job_id))
    return JobRead.model_validate(job)


@router.patch("/{job_id}", response_model=JobRead)
async def update_job(
    job_id: uuid.UUID,
    data: JobUpdate,
    db: AsyncSession = Depends(get_db),
) -> JobRead:
    job = await job_service.get_job(db, job_id)
    if not job:
        raise NotFoundError("Job", str(job_id))
    updated = await job_service.update_job(db, job, data)
    return JobRead.model_validate(updated)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    job = await job_service.get_job(db, job_id)
    if not job:
        raise NotFoundError("Job", str(job_id))
    await job_service.delete_job(db, job)
