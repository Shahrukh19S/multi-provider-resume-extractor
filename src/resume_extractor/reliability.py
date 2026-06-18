"""Milestone 5: reliability layer — fallback chain + refusal detection.

Builds on the per-call guards already in `extract.py`:
- **transport retries** (`tenacity`): 429 / 5xx / timeouts, with backoff + jitter,
  logged via `before_sleep`.
- **validation-retries** (`instructor max_retries`): re-ask on malformed answers.

This module adds the **provider fallback chain** (Gemini → Groq → GitHub Models):
if a provider exhausts its retries, errors, or **refuses**, move to the next one.
A refusal is detected and surfaced as a failed attempt — never stored as data
(rule #8). Each run records per-provider attempts so retry/fallback/refusal counts
are observable (METRICS-SPEC §4).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .extract import (
    extract_resume,
    extract_resume_from_pdf,
    extract_resume_from_pdf_text,
)
from .providers import PROVIDERS
from .schema import Resume

_log = logging.getLogger("resume_extractor.reliability")

# Default order: primary → fallback → third (CLAUDE.md provider stack).
DEFAULT_CHAIN: tuple[str, ...] = ("gemini", "groq", "github")

# Substrings that mark a safety refusal / content block across providers.
_REFUSAL_MARKERS = (
    "safety",
    "blocked",
    "block_reason",
    "content_filter",
    "content_management_policy",
    "responsibleaipolicy",
    "prohibited",
    "refus",  # "refused", "refusal"
)


class AllProvidersFailed(RuntimeError):
    """Raised when every provider in the chain failed (or refused)."""

    def __init__(self, attempts: list[Attempt]) -> None:
        self.attempts = attempts
        summary = ", ".join(
            f"{a.provider}({'refused' if a.refused else 'error'})" for a in attempts
        )
        super().__init__(f"all providers failed: {summary}")


@dataclass
class Attempt:
    provider: str
    ok: bool
    refused: bool = False
    error: str | None = None


@dataclass
class FallbackResult:
    resume: Resume
    provider: str  # the provider that succeeded
    attempts: list[Attempt] = field(default_factory=list)

    @property
    def fallback_count(self) -> int:
        """How many providers failed before the one that succeeded."""
        return sum(1 for a in self.attempts if not a.ok)

    @property
    def refusals(self) -> int:
        return sum(1 for a in self.attempts if a.refused)


def is_refusal(exc: BaseException) -> bool:
    """Heuristically detect a safety refusal / content block from any provider."""
    msg = str(exc).lower()
    return any(m in msg for m in _REFUSAL_MARKERS)


def _extract_one(source: Any, provider: str, is_pdf: bool) -> Resume:
    """Dispatch one extraction for a provider (right PDF path per provider)."""
    if not is_pdf:
        return extract_resume(source, provider=provider)
    if PROVIDERS[provider].multimodal_pdf:
        return extract_resume_from_pdf(source)  # Gemini: PDF direct
    return extract_resume_from_pdf_text(source, provider=provider)  # text-only path


def extract_with_fallback(
    source: str | Path,
    *,
    providers: tuple[str, ...] = DEFAULT_CHAIN,
    is_pdf: bool = False,
) -> FallbackResult:
    """Extract a `Resume`, falling back through `providers` on failure/refusal.

    `source` is resume text (is_pdf=False) or a PDF path (is_pdf=True). Each
    provider call already carries transport- and validation-retries; this walks the
    chain and logs counts. Raises `AllProvidersFailed` if none succeed.
    """
    attempts: list[Attempt] = []
    for provider in providers:
        try:
            resume = _extract_one(source, provider, is_pdf)
        except Exception as exc:  # noqa: BLE001 — classify, record, fall back
            refused = is_refusal(exc)
            attempts.append(
                Attempt(provider, ok=False, refused=refused, error=str(exc)[:200])
            )
            _log.warning(
                "provider %s failed (refused=%s) -> falling back: %s",
                provider,
                refused,
                str(exc)[:160],
            )
            continue

        attempts.append(Attempt(provider, ok=True))
        result = FallbackResult(resume=resume, provider=provider, attempts=attempts)
        if result.fallback_count:
            _log.info(
                "succeeded on %s after %d fallback(s) (%d refusal(s))",
                provider,
                result.fallback_count,
                result.refusals,
            )
        return result

    _log.error("all %d providers failed: %s", len(providers), attempts)
    raise AllProvidersFailed(attempts)
