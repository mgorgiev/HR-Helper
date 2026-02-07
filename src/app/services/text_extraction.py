import asyncio
from pathlib import Path

import pdfplumber
from docx import Document

from app.core.exceptions import ExtractionError


def extract_text_from_pdf(file_path: Path) -> str:
    try:
        with pdfplumber.open(file_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
            return "\n\n".join(pages).strip()
    except Exception as e:
        raise ExtractionError(f"PDF extraction failed: {e}") from e


def extract_text_from_docx(file_path: Path) -> str:
    try:
        doc = Document(str(file_path))
        return "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())
    except Exception as e:
        raise ExtractionError(f"DOCX extraction failed: {e}") from e


def extract_text_from_txt(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return file_path.read_text(encoding="latin-1")
    except Exception as e:
        raise ExtractionError(f"TXT extraction failed: {e}") from e


EXTRACTORS: dict[str, type[None] | object] = {
    ".pdf": extract_text_from_pdf,
    ".docx": extract_text_from_docx,
    ".txt": extract_text_from_txt,
}


def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    extractor = EXTRACTORS.get(suffix)
    if not extractor:
        raise ExtractionError(f"Unsupported file type: {suffix}")
    return extractor(file_path)  # type: ignore[operator]


async def extract_text_async(file_path: Path) -> str:
    return await asyncio.to_thread(extract_text, file_path)
