from google import genai

from app.core.config import get_settings


def get_gemini_client() -> genai.Client:
    """Create a Gemini API client using the configured API key."""
    settings = get_settings()
    return genai.Client(api_key=settings.google_ai_api_key)
