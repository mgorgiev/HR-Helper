from google import genai


async def generate_embedding(
    client: genai.Client,
    text: str,
    model: str,
    task_type: str = "RETRIEVAL_DOCUMENT",
) -> list[float]:
    """Generate an embedding vector for the given text using Gemini."""
    result = await client.aio.models.embed_content(
        model=model,
        contents=text,
        config={"task_type": task_type},
    )
    return list(result.embeddings[0].values)


def _build_resume_text(parsed_data: dict) -> str:
    """Combine parsed resume fields into a single text for embedding."""
    parts: list[str] = []

    if parsed_data.get("summary"):
        parts.append(parsed_data["summary"])

    skills = parsed_data.get("skills", [])
    if skills:
        parts.append(f"Skills: {', '.join(skills)}")

    for exp in parsed_data.get("experience", []):
        line = f"{exp.get('title', '')} at {exp.get('company', '')}"
        if exp.get("description"):
            line += f" — {exp['description']}"
        parts.append(line)

    for edu in parsed_data.get("education", []):
        degree = edu.get("degree", "")
        field = edu.get("field", "")
        institution = edu.get("institution", "")
        line = f"{degree} in {field} from {institution}"
        parts.append(line)

    return "\n".join(parts) if parts else "No resume data available"


async def embed_resume(
    client: genai.Client,
    model: str,
    parsed_data: dict,
) -> list[float]:
    """Build text from parsed resume data and generate its embedding."""
    text = _build_resume_text(parsed_data)
    return await generate_embedding(client, text, model, task_type="RETRIEVAL_DOCUMENT")


async def embed_job(
    client: genai.Client,
    model: str,
    title: str,
    description: str | None,
    requirements: str | None,
) -> list[float]:
    """Build text from job fields and generate its embedding."""
    parts = [title]
    if description:
        parts.append(description)
    if requirements:
        parts.append(f"Requirements: {requirements}")
    text = "\n".join(parts)
    return await generate_embedding(client, text, model, task_type="RETRIEVAL_DOCUMENT")
