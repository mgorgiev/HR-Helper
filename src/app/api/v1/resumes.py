import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_file_storage
from app.core.config import get_settings
from app.core.exceptions import ExtractionError, FileValidationError, NotFoundError
from app.schemas.resume import ResumeRead, ResumeTextResponse
from app.services import candidate_service, resume_service
from app.services.text_extraction import extract_text_async
from app.storage.base import FileStorage

router = APIRouter(tags=["resumes"])


def _validate_upload(file: UploadFile) -> None:
    settings = get_settings()
    if not file.filename:
        raise FileValidationError("Filename is required")

    ext = Path(file.filename).suffix.lower()
    if ext not in settings.allowed_extensions:
        raise FileValidationError(
            f"File type '{ext}' not allowed. Allowed: {', '.join(settings.allowed_extensions)}"
        )


@router.post(
    "/candidates/{candidate_id}/resumes",
    response_model=ResumeRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_resume(
    candidate_id: uuid.UUID,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    storage: FileStorage = Depends(get_file_storage),
) -> ResumeRead:
    # 1. Verify candidate exists
    candidate = await candidate_service.get_candidate(db, candidate_id)
    if not candidate:
        raise NotFoundError("Candidate", str(candidate_id))

    # 2. Validate file
    _validate_upload(file)

    # 3. Read content and check size
    settings = get_settings()
    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise FileValidationError(f"File size exceeds maximum of {settings.max_upload_size_mb}MB")

    # 4. Store file
    original_filename = file.filename or "unknown"
    ext = Path(original_filename).suffix.lower()
    stored_filename = f"{uuid.uuid4()}{ext}"
    file_path = await storage.save(content, stored_filename, subdir=str(candidate_id))

    # 5. Create DB record
    resume = await resume_service.create_resume(
        db,
        candidate_id=candidate_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=file_path,
        content_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(content),
    )

    # 6. Extract text
    try:
        abs_path = await storage.retrieve(file_path)
        text = await extract_text_async(abs_path)
        await resume_service.update_extraction(db, resume, text=text, status="completed")
    except (ExtractionError, Exception) as e:
        await resume_service.update_extraction(db, resume, error=str(e), status="failed")

    await db.refresh(resume)
    return ResumeRead.model_validate(resume)


@router.get("/candidates/{candidate_id}/resumes", response_model=list[ResumeRead])
async def list_resumes(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ResumeRead]:
    candidate = await candidate_service.get_candidate(db, candidate_id)
    if not candidate:
        raise NotFoundError("Candidate", str(candidate_id))
    resumes = await resume_service.list_resumes_for_candidate(db, candidate_id)
    return [ResumeRead.model_validate(r) for r in resumes]


@router.get("/resumes/{resume_id}", response_model=ResumeRead)
async def get_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ResumeRead:
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise NotFoundError("Resume", str(resume_id))
    return ResumeRead.model_validate(resume)


@router.get("/resumes/{resume_id}/download")
async def download_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: FileStorage = Depends(get_file_storage),
) -> FileResponse:
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise NotFoundError("Resume", str(resume_id))

    abs_path = await storage.retrieve(resume.file_path)
    return FileResponse(
        path=str(abs_path),
        filename=resume.original_filename,
        media_type=resume.content_type,
    )


@router.post("/resumes/{resume_id}/extract", response_model=ResumeRead)
async def re_extract_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: FileStorage = Depends(get_file_storage),
) -> ResumeRead:
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise NotFoundError("Resume", str(resume_id))

    try:
        abs_path = await storage.retrieve(resume.file_path)
        text = await extract_text_async(abs_path)
        await resume_service.update_extraction(db, resume, text=text, status="completed")
    except (ExtractionError, Exception) as e:
        await resume_service.update_extraction(db, resume, error=str(e), status="failed")

    await db.refresh(resume)
    return ResumeRead.model_validate(resume)


@router.get("/resumes/{resume_id}/text", response_model=ResumeTextResponse)
async def get_resume_text(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ResumeTextResponse:
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise NotFoundError("Resume", str(resume_id))
    return ResumeTextResponse(
        id=resume.id,
        extracted_text=resume.extracted_text,
        extraction_status=resume.extraction_status,
    )


@router.delete("/resumes/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: FileStorage = Depends(get_file_storage),
) -> None:
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise NotFoundError("Resume", str(resume_id))

    # Delete file from storage
    if await storage.exists(resume.file_path):
        await storage.delete(resume.file_path)

    await resume_service.delete_resume(db, resume)
