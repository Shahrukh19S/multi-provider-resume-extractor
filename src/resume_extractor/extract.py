"""Milestone 2: single-provider extraction via Gemini native structured outputs.

Takes resume *text* and returns a validated `Resume`. Uses `instructor` over the
google-genai SDK in `Mode.JSON` — Gemini's native structured outputs
(`response_mime_type=application/json` + `response_schema`), the preferred path
per CLAUDE.md rule #2. temperature=0, pinned model (rules #4/#5).

A minimal `tenacity` retry guards the call against free-tier 429s (CHANGE-BRIEF
adjustment #6: "wire tenacity retries for 429s early"). The full reliability layer
— provider fallback chain, validation-retry/refusal accounting — is Milestone 5.

PDF ingestion (direct multimodal for Gemini, text extraction for text-only
providers) arrives in Milestone 3; this milestone works from text.
"""

from __future__ import annotations

import os

import instructor
from dotenv import load_dotenv
from google import genai
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .config import GEMINI_MODEL, TEMPERATURE
from .schema import Resume

# The "don't hallucinate" rule lives in the prompt (BUILD-PLAN design note):
# missing fields must come back null/empty rather than invented.
SYSTEM_PROMPT = (
    "You extract structured data from resume / CV text. "
    "Use only information explicitly present in the text. "
    "If a field is not stated, leave it null or empty — never guess, infer, or "
    "invent values. Preserve dates exactly as written (e.g. 'Present', '2019')."
)

_client: instructor.Instructor | None = None


def _gemini_client() -> instructor.Instructor:
    """Lazily build (and cache) an instructor-wrapped Gemini client in native
    structured-output mode (`Mode.JSON` for the GenAI provider)."""
    global _client
    if _client is None:
        load_dotenv()
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to .env (see .env.example)."
            )
        _client = instructor.from_genai(
            genai.Client(api_key=api_key),
            mode=instructor.Mode.JSON,
        )
    return _client


def _is_rate_limit(exc: BaseException) -> bool:
    """True for free-tier rate-limit / quota errors worth backing off on."""
    msg = str(exc).lower()
    return "429" in msg or "resource_exhausted" in msg or "rate limit" in msg


@retry(
    retry=retry_if_exception(_is_rate_limit),
    wait=wait_exponential_jitter(initial=2, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)
def extract_resume(text: str) -> Resume:
    """Extract a validated `Resume` from raw resume text using Gemini.

    Retries with exponential backoff + jitter on free-tier rate limits.
    """
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
