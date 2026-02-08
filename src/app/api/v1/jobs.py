import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from google import genai
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_llm_client, get_vector_store
from app.core.config import get_settings
from app.core.exceptions import AIServiceError, NotFoundError
from app.schemas import PaginatedResponse
from app.schemas.job import JobCreate, JobRead, JobUpdate
from app.services import embedding_service as embed_svc
from app.services import job_service, pipeline
from app.storage.vector_store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    data: JobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    llm_client: genai.Client = Depends(get_llm_client),
    vector_store: VectorStore = Depends(get_vector_store),
) -> JobRead:
    job = await job_service.create_job(db, data)

    # Trigger embedding in background
    settings = get_settings()
    background_tasks.add_task(
        pipeline.process_job_pipeline,
        db,
        job.id,
        llm_client,
        vector_store,
        settings.gemini_embedding_model,
    )

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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    llm_client: genai.Client = Depends(get_llm_client),
    vector_store: VectorStore = Depends(get_vector_store),
) -> JobRead:
    job = await job_service.get_job(db, job_id)
    if not job:
        raise NotFoundError("Job", str(job_id))
    updated = await job_service.update_job(db, job, data)

    # Re-embed if title, description, or requirements changed
    changed_fields = data.model_dump(exclude_unset=True)
    if any(f in changed_fields for f in ("title", "description", "requirements")):
        settings = get_settings()
        background_tasks.add_task(
            pipeline.process_job_pipeline,
            db,
            updated.id,
            llm_client,
            vector_store,
            settings.gemini_embedding_model,
        )

    return JobRead.model_validate(updated)


@router.post("/{job_id}/embed", response_model=JobRead)
async def embed_job_endpoint(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    llm_client: genai.Client = Depends(get_llm_client),
    vector_store: VectorStore = Depends(get_vector_store),
) -> JobRead:
    """Generate and store embedding for a job."""
    job = await job_service.get_job(db, job_id)
    if not job:
        raise NotFoundError("Job", str(job_id))

    settings = get_settings()
    try:
        embedding = await embed_svc.embed_job(
            llm_client,
            settings.gemini_embedding_model,
            job.title,
            job.description,
            job.requirements,
        )
        text = f"{job.title} {job.description or ''} {job.requirements or ''}"
        await vector_store.upsert(
            collection=settings.chromadb_collection_jobs,
            doc_id=str(job_id),
            text=text,
            embedding=embedding,
            metadata={"is_active": job.is_active},
        )
    except Exception as e:
        raise AIServiceError(str(e)) from e

    return JobRead.model_validate(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    vector_store: VectorStore = Depends(get_vector_store),
) -> None:
    job = await job_service.get_job(db, job_id)
    if not job:
        raise NotFoundError("Job", str(job_id))

    # Clean up vector store
    settings = get_settings()
    try:
        await vector_store.delete(settings.chromadb_collection_jobs, str(job_id))
    except Exception:
        logger.debug("Vector store cleanup for job %s skipped", job_id)

    await job_service.delete_job(db, job)
