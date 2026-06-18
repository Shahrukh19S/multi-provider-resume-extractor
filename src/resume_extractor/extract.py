"""Extraction calls — one interface over multiple providers.

- `extract_resume(text, provider=...)` — text extraction via any provider
  (gemini / groq / github), same signature, swap by name (Milestones 2 & 4).
- `extract_resume_from_pdf(path)` — Gemini **multimodal**: send the PDF directly
  (Milestone 3; Gemini only — it's the one provider that reads PDFs natively).
- `extract_resume_from_pdf_text(path, provider=...)` — pypdf text → text path
  (Milestone 3; the path text-only providers Groq / GitHub Models use).

All calls use temperature=0 and pinned model IDs (rules #4/#5) and prefer native
structured outputs, falling back to tool-forcing per provider (rule #2; see
`providers.py`). A minimal `tenacity` retry guards transient transport errors —
429 rate limits and 5xx/timeouts, common on free tiers (CHANGE-BRIEF #6, rule #8).
The full reliability layer (provider fallback chain, validation-retry/refusal
accounting) is Milestone 5.
"""

from __future__ import annotations

import logging
from pathlib import Path

from google.genai import types
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .config import GEMINI_MODEL, TEMPERATURE
from .ingest import pdf_to_text
from .providers import PROVIDERS, gemini_raw_client, text_client
from .schema import Resume

_log = logging.getLogger("resume_extractor.extract")

# instructor re-asks the model this many times on a pydantic ValidationError
# (malformed answer) before giving up — rule #8 "validation-retries".
VALIDATION_RETRIES = 2

# The "don't hallucinate" rule lives in the prompt (BUILD-PLAN design note):
# missing fields must come back null/empty rather than invented.
SYSTEM_PROMPT = (
    "You extract structured data from resume / CV text. "
    "Use only information explicitly present in the text. "
    "If a field is not stated, leave it null or empty — never guess, infer, or "
    "invent values. Preserve dates exactly as written (e.g. 'Present', '2019')."
)


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
    before_sleep=before_sleep_log(_log, logging.WARNING),  # log each transport retry
    reraise=True,
)


@_transient_retry
def extract_resume(text: str, provider: str = "gemini") -> Resume:
    """Extract a validated `Resume` from resume *text* using any provider.

    `provider` is one of "gemini", "groq", "github" — same call, swap by name.
    """
    client = text_client(provider)
    return client.chat.completions.create(
        model=PROVIDERS[provider].model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_model=Resume,
        max_retries=VALIDATION_RETRIES,  # instructor validation-retries (rule #8)
        temperature=TEMPERATURE,
    )


@_transient_retry
def extract_resume_with_usage(
    text: str, provider: str = "gemini"
) -> tuple[Resume, object]:
    """Like `extract_resume`, but also returns the raw provider response so token
    usage can be read (Milestone 6 cost accounting). See `costs.usage_from_completion`."""
    client = text_client(provider)
    resume, completion = client.chat.completions.create_with_completion(
        model=PROVIDERS[provider].model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_model=Resume,
        max_retries=VALIDATION_RETRIES,
        temperature=TEMPERATURE,
    )
    return resume, completion


@_transient_retry
def extract_resume_from_pdf(path: str | Path) -> Resume:
    """Gemini **multimodal** path (M3): send the PDF directly, no pre-extraction.

    Best for messy multi-column layouts and scanned/image PDFs. Uses Gemini's
    native structured outputs (`response_schema=Resume`). Gemini-only — text-only
    providers must use `extract_resume_from_pdf_text`.
    """
    client = gemini_raw_client()
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


def extract_resume_from_pdf_text(path: str | Path, provider: str = "gemini") -> Resume:
    """Text path (M3): pypdf text extraction → the text extractor for `provider`.

    This is the path text-only providers (Groq, GitHub Models) use for PDFs.
    """
    return extract_resume(pdf_to_text(path), provider=provider)
