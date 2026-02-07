"""Unit tests for the text extraction service."""

from pathlib import Path

import pytest

from app.core.exceptions import ExtractionError
from app.services.text_extraction import (
    EXTRACTORS,
    extract_text,
    extract_text_from_docx,
    extract_text_from_pdf,
    extract_text_from_txt,
)

pytestmark = pytest.mark.unit


class TestExtractTextFromPDF:
    def test_extract_pdf_returns_text(self, sample_pdf: Path) -> None:
        text = extract_text_from_pdf(sample_pdf)
        assert isinstance(text, str)
        assert len(text) > 0
        assert "ALEX JOHNSON" in text.upper()


class TestExtractTextFromDOCX:
    def test_extract_docx_returns_text(self, sample_docx: Path) -> None:
        text = extract_text_from_docx(sample_docx)
        assert isinstance(text, str)
        assert len(text) > 0
        assert "JANE SMITH" in text.upper()


class TestExtractTextFromTXT:
    def test_extract_txt_returns_text(self, sample_txt: Path) -> None:
        text = extract_text_from_txt(sample_txt)
        assert isinstance(text, str)
        assert len(text) > 0
        assert "JOHN DOE" in text
        assert "Software Engineer" in text

    def test_extract_txt_latin1_fallback(self, tmp_path: Path) -> None:
        content = "R\u00e9sum\u00e9 of Ren\u00e9 M\u00fcller"
        file_path = tmp_path / "latin1_resume.txt"
        file_path.write_bytes(content.encode("latin-1"))

        text = extract_text_from_txt(file_path)
        assert "sum" in text
        assert "Ren" in text
        assert "ller" in text


class TestExtractText:
    def test_extract_unsupported_extension_raises(self, tmp_path: Path) -> None:
        xlsx_file = tmp_path / "spreadsheet.xlsx"
        xlsx_file.write_bytes(b"fake xlsx content")

        with pytest.raises(ExtractionError, match="Unsupported file type"):
            extract_text(xlsx_file)

    def test_extract_corrupted_pdf_raises(self, tmp_path: Path) -> None:
        corrupted_pdf = tmp_path / "corrupted.pdf"
        corrupted_pdf.write_bytes(b"this is not a valid pdf at all\x00\x01\x02")

        with pytest.raises(ExtractionError, match="PDF extraction failed"):
            extract_text(corrupted_pdf)

    def test_extract_empty_pdf(self, tmp_path: Path) -> None:
        """A valid PDF with a blank page should return empty or whitespace-only text."""
        # Minimal valid PDF with one empty page (no text objects)
        empty_pdf_bytes = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
            b"xref\n0 4\n"
            b"0000000000 65535 f \n"
            b"0000000009 00000 n \n"
            b"0000000058 00000 n \n"
            b"0000000115 00000 n \n"
            b"trailer<</Size 4/Root 1 0 R>>\n"
            b"startxref\n190\n%%EOF"
        )
        empty_pdf_path = tmp_path / "empty.pdf"
        empty_pdf_path.write_bytes(empty_pdf_bytes)

        text = extract_text(empty_pdf_path)
        assert isinstance(text, str)
        assert text.strip() == ""


class TestExtractorsDict:
    def test_extractors_has_expected_keys(self) -> None:
        assert ".pdf" in EXTRACTORS
        assert ".docx" in EXTRACTORS
        assert ".txt" in EXTRACTORS
