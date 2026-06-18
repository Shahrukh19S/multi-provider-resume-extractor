"""Typed multi-provider LLM client + resume extractor (Phase 2)."""

from __future__ import annotations

from .costs import PRICES, Usage, cost_per_1000, cost_usd, usage_from_completion
from .extract import (
    extract_resume,
    extract_resume_from_pdf,
    extract_resume_from_pdf_text,
    extract_resume_with_usage,
)
from .ingest import pdf_to_text
from .providers import PROVIDERS
from .reliability import (
    AllProvidersFailed,
    FallbackResult,
    extract_with_fallback,
)
from .schema import Education, Job, Resume

__all__ = [
    "PRICES",
    "PROVIDERS",
    "AllProvidersFailed",
    "Education",
    "FallbackResult",
    "Job",
    "Resume",
    "Usage",
    "cost_per_1000",
    "cost_usd",
    "extract_resume",
    "extract_resume_from_pdf",
    "extract_resume_from_pdf_text",
    "extract_resume_with_usage",
    "extract_with_fallback",
    "pdf_to_text",
    "usage_from_completion",
    "main",
]


def main() -> None:
    """CLI entry point — delegates to `resume_extractor.cli` (lazy import)."""
    from .cli import main as cli_main

    raise SystemExit(cli_main())
