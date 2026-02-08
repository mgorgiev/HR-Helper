import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume


async def create_resume(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    original_filename: str,
    stored_filename: str,
    file_path: str,
    content_type: str,
    file_size_bytes: int,
) -> Resume:
    resume = Resume(
        candidate_id=candidate_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=file_path,
        content_type=content_type,
        file_size_bytes=file_size_bytes,
    )
    db.add(resume)
    await db.flush()
    await db.refresh(resume)
    return resume


async def get_resume(db: AsyncSession, resume_id: uuid.UUID) -> Resume | None:
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    return result.scalar_one_or_none()


async def list_resumes_for_candidate(db: AsyncSession, candidate_id: uuid.UUID) -> list[Resume]:
    result = await db.execute(
        select(Resume).where(Resume.candidate_id == candidate_id).order_by(Resume.created_at.desc())
    )
    return list(result.scalars().all())


async def update_extraction(
    db: AsyncSession,
    resume: Resume,
    *,
    text: str | None = None,
    error: str | None = None,
    status: str = "completed",
) -> Resume:
    resume.extraction_status = status
    if text is not None:
        resume.extracted_text = text
    if error is not None:
        resume.extraction_error = error
    await db.flush()
    await db.refresh(resume)
    return resume


async def update_parsing(
    db: AsyncSession,
    resume: Resume,
    *,
    parsed_data: dict | None = None,
    error: str | None = None,
    status: str = "completed",
) -> Resume:
    resume.parsing_status = status
    if parsed_data is not None:
        resume.parsed_data = parsed_data
        resume.parsed_at = datetime.now(UTC)
    if error is not None:
        resume.parsing_error = error
    await db.flush()
    await db.refresh(resume)
    return resume


async def delete_resume(db: AsyncSession, resume: Resume) -> None:
    await db.delete(resume)
    await db.flush()
