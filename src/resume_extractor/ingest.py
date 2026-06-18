"""Milestone 3: PDF ingestion — the text-extraction path.

Two ingestion paths exist in the project:

- **Gemini (primary):** send the PDF *directly* as multimodal input — best for
  messy, multi-column layouts where flat text extraction scrambles reading order.
  That path lives in `extract.extract_resume_from_pdf` (next to the model call).
- **Text-only providers (Groq, GitHub Models):** extract text first with `pypdf`,
  then run the normal text extraction. That path lives here.

Measuring the two approaches on a messy resume is the M3 deliverable (BENCHMARK.md).
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def pdf_to_text(path: str | Path) -> str:
    """Extract plain text from a PDF with pypdf (the text-only-provider path).

    Raises ValueError on a PDF with no extractable text (e.g. a scanned/image-only
    resume) — those must go through the Gemini multimodal path instead.
    """
    reader = PdfReader(str(path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    if not text:
        raise ValueError(
            f"No extractable text in {path} (scanned/image-only PDF?). "
            "Use the Gemini multimodal path (extract_resume_from_pdf) instead."
        )
    return text
