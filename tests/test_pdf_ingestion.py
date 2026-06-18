"""Milestone 3: PDF ingestion (both paths).

Auto-discovers PDFs in tests/sample_resumes/. Skips cleanly when none are present
or when GEMINI_API_KEY is unset, so `uv run pytest` stays green on a fresh clone.
Drop a resume PDF into tests/sample_resumes/ to exercise these.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from resume_extractor.extract import extract_resume_from_pdf
from resume_extractor.ingest import pdf_to_text
from resume_extractor.schema import Resume

load_dotenv()

SAMPLE_DIR = Path(__file__).parent / "sample_resumes"
PDFS = sorted(SAMPLE_DIR.glob("*.pdf")) if SAMPLE_DIR.exists() else []

needs_pdf = pytest.mark.skipif(
    not PDFS, reason="no PDF in tests/sample_resumes/ — drop one in to run"
)
needs_key = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set — add it to .env",
)


@needs_pdf
def test_text_path_extracts_text():
    """pypdf text path yields text for at least one (non-scanned) sample PDF."""
    texts = []
    for p in PDFS:
        try:
            texts.append(pdf_to_text(p))
        except ValueError:
            pass  # image-only PDF — only valid via the multimodal path
    if not texts:
        pytest.skip("all sample PDFs are image-only; text path needs a text PDF")
    assert any(t.strip() for t in texts)


@needs_pdf
@needs_key
def test_gemini_multimodal_pdf_extracts():
    """Gemini multimodal path returns a validated Resume from a real PDF."""
    resume = extract_resume_from_pdf(PDFS[0])
    assert isinstance(resume, Resume)
    assert resume.full_name and resume.full_name.strip()
