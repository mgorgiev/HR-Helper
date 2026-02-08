import logging
import uuid

from google import genai
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import embedding_service, job_service, resume_service
from app.services.resume_parser import parse_resume
from app.storage.vector_store import VectorStore

logger = logging.getLogger(__name__)


async def process_resume_pipeline(
    db: AsyncSession,
    resume_id: uuid.UUID,
    llm_client: genai.Client,
    vector_store: VectorStore,
    gemini_model: str,
    embedding_model: str,
) -> None:
    """Full pipeline: parse with Gemini -> embed -> store in ChromaDB."""
    resume = await resume_service.get_resume(db, resume_id)
    if not resume or not resume.extracted_text:
        return

    # Step 1: Parse
    try:
        parsed = await parse_resume(llm_client, resume.extracted_text, gemini_model)
        await resume_service.update_parsing(
            db, resume, parsed_data=parsed.model_dump(), status="completed"
        )
    except Exception as e:
        logger.error("Resume %s parsing failed: %s", resume_id, e)
        await resume_service.update_parsing(db, resume, error=str(e), status="failed")
        return  # Don't embed if parsing failed

    # Step 2: Embed
    try:
        embedding = await embedding_service.embed_resume(
            llm_client, embedding_model, parsed.model_dump()
        )
        await vector_store.upsert(
            collection="resumes",
            doc_id=str(resume_id),
            text=resume.extracted_text,
            embedding=embedding,
            metadata={"candidate_id": str(resume.candidate_id)},
        )
    except Exception as e:
        logger.error("Resume %s embedding failed: %s", resume_id, e)

    await db.flush()


async def process_job_pipeline(
    db: AsyncSession,
    job_id: uuid.UUID,
    llm_client: genai.Client,
    vector_store: VectorStore,
    embedding_model: str,
) -> None:
    """Embed a job description and store in ChromaDB."""
    job = await job_service.get_job(db, job_id)
    if not job:
        return

    try:
        embedding = await embedding_service.embed_job(
            llm_client, embedding_model, job.title, job.description, job.requirements
        )
        text = f"{job.title} {job.description or ''} {job.requirements or ''}"
        await vector_store.upsert(
            collection="jobs",
            doc_id=str(job_id),
            text=text,
            embedding=embedding,
            metadata={"is_active": job.is_active},
        )
    except Exception as e:
        logger.error("Job %s embedding failed: %s", job_id, e)
