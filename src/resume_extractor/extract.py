"""Extraction calls.

Milestone 2 — single-provider extraction from **text** via Gemini native
structured outputs (`instructor` over google-genai, `Mode.JSON`).
Milestone 3 — PDF ingestion, two paths:
  * `extract_resume_from_pdf(path)` — Gemini **multimodal**: send the PDF directly.
  * `extract_resume_from_pdf_text(path)` — pypdf text extraction → text path
    (what text-only providers like Groq / GitHub Models will use in M4).

All calls use temperature=0 and the pinned model (rules #4/#5) and prefer native
structured outputs (rule #2). A minimal `tenacity` retry guards against transient
transport errors — 429 rate limits and 5xx/unavailable/timeouts, common on free
tiers (CHANGE-BRIEF #6, rule #8); the full reliability layer (provider fallback
chain, validation-retry/refusal accounting) is Milestone 5.

Design note: the text path goes through `instructor` (unifies providers + gives
validation-retries). The Gemini *multimodal* path calls google-genai directly with
a Pydantic `response_schema` — still native structured outputs, but instructor's
multimodal genai wrapper isn't cleanly exposed in this version, so the direct SDK
call is the controllable, verifiable choice.
"""

from __future__ import annotations

import os
from pathlib import Path

import instructor
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .config import GEMINI_MODEL, TEMPERATURE
from .ingest import pdf_to_text
from .schema import Resume

# The "don't hallucinate" rule lives in the prompt (BUILD-PLAN design note):
# missing fields must come back null/empty rather than invented.
SYSTEM_PROMPT = (
    "You extract structured data from resume / CV text. "
    "Use only information explicitly present in the text. "
    "If a field is not stated, leave it null or empty — never guess, infer, or "
    "invent values. Preserve dates exactly as written (e.g. 'Present', '2019')."
)

_raw_client: genai.Client | None = None
_instructor_client: instructor.Instructor | None = None


def _api_key() -> str:
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to .env (see .env.example)."
        )
    return api_key


def _genai_client() -> genai.Client:
    """Cached raw google-genai client (used for the multimodal PDF path)."""
    global _raw_client
    if _raw_client is None:
        _raw_client = genai.Client(api_key=_api_key())
    return _raw_client


def _gemini_client() -> instructor.Instructor:
    """Cached instructor-wrapped Gemini client in native structured-output mode."""
    global _instructor_client
    if _instructor_client is None:
        _instructor_client = instructor.from_genai(
            _genai_client(), mode=instructor.Mode.JSON
        )
    return _instructor_client


def _is_transient(exc: BaseException) -> bool:
    """True for transient transport errors worth backing off on (rule #8):
    rate-limits (429), and 5xx / unavailable / overloaded / timeouts. Free tiers
    return these often, especially 429 (quota) and 503 (high demand)."""
    msg = str(exc).lower()
    needles = (
        "429",
        "resource_exhausted",
        "rate limit",
        "unavailable",  # 503
        "overloaded",
        "internal",  # 500
        "deadline",  # 504 deadline_exceeded
        "timeout",
    )
    return any(n in msg for n in needles)


_transient_retry = retry(
    retry=retry_if_exception(_is_transient),
    wait=wait_exponential_jitter(initial=2, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)


@_transient_retry
def extract_resume(text: str) -> Resume:
    """Extract a validated `Resume` from raw resume *text* using Gemini (M2)."""
    client = _gemini_client()
    return client.chat.completions.create(
        model=GEMINI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_model=Resume,
        temperature=TEMPERATURE,
    )


@_transient_retry
def extract_resume_from_pdf(path: str | Path) -> Resume:
    """Gemini **multimodal** path (M3): send the PDF directly, no pre-extraction.

    Best for messy multi-column layouts and scanned/image PDFs. Uses Gemini's
    native structured outputs (`response_schema=Resume`).
    """
    client = _genai_client()
    pdf_bytes = Path(path).read_bytes()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            "Extract the structured resume from this document.",
        ],
        config=types.GenerateContentConfig(
            temperature=TEMPERATURE,
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=Resume,
        ),
    )
    parsed = response.parsed
    if isinstance(parsed, Resume):
        return parsed
    # Fallback if the SDK didn't auto-parse for some reason.
    return Resume.model_validate_json(response.text or "")


def extract_resume_from_pdf_text(path: str | Path) -> Resume:
    """Text path (M3): pypdf text extraction → the M2 text extractor.

    This is the path text-only providers (Groq, GitHub Models) will reuse in M4.
    """
    return extract_resume(pdf_to_text(path))
