import json
import logging

from google import genai
from google.genai import types

from app.schemas.parsed_resume import ParsedResumeData

logger = logging.getLogger(__name__)

PARSE_PROMPT = (
    "You are a resume parser. Extract structured information "
    "from the following resume text.\n"
    "Be thorough — extract all skills, work experience, "
    "and education entries.\n"
    "If a field is not found, leave it as null or empty list.\n\n"
    "Resume text:\n{text}"
)


async def parse_resume(
    client: genai.Client,
    extracted_text: str,
    model: str,
) -> ParsedResumeData:
    """Send extracted text to Gemini and get structured resume data back."""
    response = await client.aio.models.generate_content(
        model=model,
        contents=PARSE_PROMPT.format(text=extracted_text),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ParsedResumeData,
            temperature=0.1,
        ),
    )

    raw = response.text
    if not raw:
        return ParsedResumeData()

    data = json.loads(raw)
    return ParsedResumeData.model_validate(data)
