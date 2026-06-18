"""Typed multi-provider LLM client + resume extractor (Phase 2)."""

from __future__ import annotations

from .extract import (
    extract_resume,
    extract_resume_from_pdf,
    extract_resume_from_pdf_text,
)
from .ingest import pdf_to_text
from .schema import Education, Job, Resume

__all__ = [
    "Education",
    "Job",
    "Resume",
    "extract_resume",
    "extract_resume_from_pdf",
    "extract_resume_from_pdf_text",
    "pdf_to_text",
    "main",
]


def main() -> None:
    """Placeholder CLI entrypoint (built out in Milestone 9)."""
    print("resume-extractor — see `uv run python -m resume_extractor.sanity`")
