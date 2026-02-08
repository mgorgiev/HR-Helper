import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, status
from fastapi.responses import FileResponse
from google import genai
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_file_storage, get_llm_client, get_vector_store
from app.core.config import get_settings
from app.core.exceptions import (
    AIServiceError,
    ExtractionError,
    FileValidationError,
    NotFoundError,
    PreconditionError,
)
from app.schemas.resume import ResumeParsedResponse, ResumeRead, ResumeTextResponse
from app.services import candidate_service, pipeline, resume_service
from app.services import embedding_service as embed_svc
from app.services.resume_parser import parse_resume
from app.services.text_extraction import extract_text_async
from app.storage.base import FileStorage
from app.storage.vector_store import VectorStore

logger = logging.getLogger(__name__)

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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    storage: FileStorage = Depends(get_file_storage),
    llm_client: genai.Client = Depends(get_llm_client),
    vector_store: VectorStore = Depends(get_vector_store),
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

    # 7. Trigger AI pipeline in background (parse + embed)
    if resume.extraction_status == "completed" and resume.extracted_text:
        background_tasks.add_task(
            pipeline.process_resume_pipeline,
            db,
            resume.id,
            llm_client,
            vector_store,
            settings.gemini_model,
            settings.gemini_embedding_model,
        )

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


@router.post("/resumes/{resume_id}/parse", response_model=ResumeRead)
async def parse_resume_endpoint(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    llm_client: genai.Client = Depends(get_llm_client),
) -> ResumeRead:
    """Trigger Gemini parsing for a resume."""
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise NotFoundError("Resume", str(resume_id))

    if not resume.extracted_text:
        raise PreconditionError("Resume has no extracted text. Run extraction first.")

    settings = get_settings()
    try:
        parsed = await parse_resume(llm_client, resume.extracted_text, settings.gemini_model)
        await resume_service.update_parsing(
            db, resume, parsed_data=parsed.model_dump(), status="completed"
        )
    except Exception as e:
        await resume_service.update_parsing(db, resume, error=str(e), status="failed")
        raise AIServiceError(str(e)) from e

    await db.refresh(resume)
    return ResumeRead.model_validate(resume)


@router.get("/resumes/{resume_id}/parsed", response_model=ResumeParsedResponse)
async def get_parsed_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ResumeParsedResponse:
    """Get just the parsed structured data."""
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise NotFoundError("Resume", str(resume_id))
    return ResumeParsedResponse(
        id=resume.id,
        parsed_data=resume.parsed_data,
        parsing_status=resume.parsing_status,
        parsing_error=resume.parsing_error,
    )


@router.post("/resumes/{resume_id}/embed", response_model=ResumeRead)
async def embed_resume_endpoint(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    llm_client: genai.Client = Depends(get_llm_client),
    vector_store: VectorStore = Depends(get_vector_store),
) -> ResumeRead:
    """Generate and store embedding for a resume."""
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise NotFoundError("Resume", str(resume_id))

    if not resume.parsed_data:
        raise PreconditionError("Resume has no parsed data. Run parsing first.")

    settings = get_settings()
    try:
        embedding = await embed_svc.embed_resume(
            llm_client, settings.gemini_embedding_model, resume.parsed_data
        )
        await vector_store.upsert(
            collection=settings.chromadb_collection_resumes,
            doc_id=str(resume_id),
            text=resume.extracted_text or "",
            embedding=embedding,
            metadata={"candidate_id": str(resume.candidate_id)},
        )
    except Exception as e:
        raise AIServiceError(str(e)) from e

    await db.refresh(resume)
    return ResumeRead.model_validate(resume)


@router.delete("/resumes/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: FileStorage = Depends(get_file_storage),
    vector_store: VectorStore = Depends(get_vector_store),
) -> None:
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise NotFoundError("Resume", str(resume_id))

    # Delete file from storage
    if await storage.exists(resume.file_path):
        await storage.delete(resume.file_path)

    # Clean up vector store (ignore errors if not embedded)
    settings = get_settings()
    try:
        await vector_store.delete(settings.chromadb_collection_resumes, str(resume_id))
    except Exception:
        logger.debug("Vector store cleanup for resume %s skipped", resume_id)

    await resume_service.delete_resume(db, resume)
