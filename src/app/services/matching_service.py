import json
import logging
import uuid

from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.schemas.match import CandidateMatch, JobMatch
from app.services import candidate_service, job_service, resume_service
from app.services.embedding_service import generate_embedding
from app.storage.vector_store import VectorStore

logger = logging.getLogger(__name__)


def _distance_to_score(distance: float) -> float:
    """Convert cosine distance to a 0-1 similarity score."""
    # Cosine distance ranges from 0 (identical) to 2 (opposite)
    # Score = 1 - (distance / 2) maps to 1.0 (identical) to 0.0 (opposite)
    return max(0.0, min(1.0, 1.0 - distance / 2))


async def _generate_explanations(
    client: genai.Client,
    model: str,
    reference_text: str,
    match_texts: list[str],
    match_labels: list[str],
) -> list[str]:
    """Ask Gemini to explain why each match is relevant."""
    if not match_texts:
        return []

    matches_block = ""
    for label, text in zip(match_labels, match_texts, strict=True):
        matches_block += f"\n--- {label} ---\n{text}\n"

    prompt = (
        "You are an HR matching assistant. For each candidate/job below, "
        "explain in 1-2 sentences why they are a good or poor match for "
        "the reference.\n\n"
        f"Reference:\n{reference_text}\n\n"
        f"Matches:\n{matches_block}\n\n"
        "Return a JSON array of strings, one explanation per match, "
        "in the same order."
    )

    response = await client.aio.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )

    try:
        explanations = json.loads(response.text or "[]")
        if isinstance(explanations, list):
            # Pad with fallback if Gemini returns fewer than expected
            while len(explanations) < len(match_texts):
                explanations.append("No explanation available.")
            return explanations[: len(match_texts)]
    except (json.JSONDecodeError, TypeError):
        pass

    return ["No explanation available."] * len(match_texts)


async def match_candidates_to_job(
    db: AsyncSession,
    client: genai.Client,
    vector_store: VectorStore,
    job: Job,
    model: str,
    embedding_model: str,
    limit: int = 10,
    min_score: float = 0.0,
) -> list[CandidateMatch]:
    """Find best matching candidates for a job."""
    # Build job text for query embedding
    job_text = f"{job.title}\n{job.description or ''}\n{job.requirements or ''}"
    query_embedding = await generate_embedding(
        client, job_text, embedding_model, task_type="RETRIEVAL_QUERY"
    )

    # Search resume embeddings
    results = await vector_store.search(
        collection="resumes",
        query_embedding=query_embedding,
        n_results=limit * 2,  # Fetch extra in case some are filtered out
    )

    if not results:
        return []

    # Build matches with scores
    matches: list[dict] = []
    for result in results:
        score = _distance_to_score(result["distance"])
        if score < min_score:
            continue

        resume_id = uuid.UUID(result["id"])
        resume = await resume_service.get_resume(db, resume_id)
        if not resume:
            continue

        candidate = await candidate_service.get_candidate(db, resume.candidate_id)
        if not candidate:
            continue

        matches.append(
            {
                "candidate_id": candidate.id,
                "resume_id": resume.id,
                "candidate_name": f"{candidate.first_name} {candidate.last_name}",
                "score": score,
                "resume_text": resume.extracted_text or "",
            }
        )

    # Sort by score and limit
    matches.sort(key=lambda m: m["score"], reverse=True)
    matches = matches[:limit]

    if not matches:
        return []

    # Generate explanations
    explanations = await _generate_explanations(
        client=client,
        model=model,
        reference_text=job_text,
        match_texts=[m["resume_text"] for m in matches],
        match_labels=[m["candidate_name"] for m in matches],
    )

    return [
        CandidateMatch(
            candidate_id=m["candidate_id"],
            resume_id=m["resume_id"],
            candidate_name=m["candidate_name"],
            score=round(m["score"], 4),
            explanation=explanations[i],
        )
        for i, m in enumerate(matches)
    ]


async def match_jobs_to_candidate(
    db: AsyncSession,
    client: genai.Client,
    vector_store: VectorStore,
    candidate_id: uuid.UUID,
    model: str,
    embedding_model: str,
    limit: int = 10,
    min_score: float = 0.0,
) -> list[JobMatch]:
    """Find best matching jobs for a candidate."""
    # Get candidate's latest resume
    resumes = await resume_service.list_resumes_for_candidate(db, candidate_id)
    if not resumes:
        return []

    # Use the most recent resume with extracted text
    resume = next((r for r in resumes if r.extracted_text), None)
    if not resume:
        return []

    # Generate query embedding from resume text
    query_embedding = await generate_embedding(
        client, resume.extracted_text or "", embedding_model, task_type="RETRIEVAL_QUERY"
    )

    # Search job embeddings
    results = await vector_store.search(
        collection="jobs",
        query_embedding=query_embedding,
        n_results=limit * 2,
    )

    if not results:
        return []

    # Build matches
    matches: list[dict] = []
    for result in results:
        score = _distance_to_score(result["distance"])
        if score < min_score:
            continue

        job_id = uuid.UUID(result["id"])
        job = await job_service.get_job(db, job_id)
        if not job:
            continue

        job_text = f"{job.title}\n{job.description or ''}\n{job.requirements or ''}"
        matches.append(
            {
                "job_id": job.id,
                "job_title": job.title,
                "score": score,
                "job_text": job_text,
            }
        )

    matches.sort(key=lambda m: m["score"], reverse=True)
    matches = matches[:limit]

    if not matches:
        return []

    # Generate explanations
    resume_text = resume.extracted_text or ""
    explanations = await _generate_explanations(
        client=client,
        model=model,
        reference_text=resume_text,
        match_texts=[m["job_text"] for m in matches],
        match_labels=[m["job_title"] for m in matches],
    )

    return [
        JobMatch(
            job_id=m["job_id"],
            job_title=m["job_title"],
            score=round(m["score"], 4),
            explanation=explanations[i],
        )
        for i, m in enumerate(matches)
    ]
