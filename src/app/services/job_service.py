import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.schemas.job import JobCreate, JobUpdate


async def create_job(db: AsyncSession, data: JobCreate) -> Job:
    job = Job(**data.model_dump())
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> Job | None:
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def list_jobs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    is_active: bool | None = None,
) -> tuple[list[Job], int]:
    query = select(Job)
    count_query = select(func.count()).select_from(Job)

    if is_active is not None:
        query = query.where(Job.is_active == is_active)
        count_query = count_query.where(Job.is_active == is_active)

    total = (await db.execute(count_query)).scalar_one()
    results = await db.execute(query.offset(skip).limit(limit).order_by(Job.created_at.desc()))
    return list(results.scalars().all()), total


async def update_job(db: AsyncSession, job: Job, data: JobUpdate) -> Job:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)
    await db.flush()
    await db.refresh(job)
    return job


async def delete_job(db: AsyncSession, job: Job) -> None:
    await db.delete(job)
    await db.flush()
