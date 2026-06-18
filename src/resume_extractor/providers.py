"""Milestone 4: multiple providers behind one interface.

All three providers are reached through `instructor`, so a single call signature
(`extract.extract_resume(text, provider=...)`) works for any of them — swap by name.

- **gemini** (primary): google-genai SDK, native structured outputs (`Mode.JSON`),
  and the only one that reads PDFs directly (multimodal — see `extract.py`).
- **groq** / **github** (text-only): OpenAI-compatible HTTP endpoints, wrapped with
  `instructor.from_openai(openai.OpenAI(base_url=...))`.

Verified live (2026-06-18): Groq base `https://api.groq.com/openai/v1`, model
`llama-3.3-70b-versatile` (production); GitHub Models base
`https://models.github.ai/inference`, model `openai/gpt-4o-mini`
(structured outputs supported on gpt-4o-mini+).

Mode per provider (rule #2: prefer native structured outputs, fall back to
tool-forcing) is recorded on each `ProviderSpec` and confirmed live.

`litellm` remains a dependency (kept for cost/token accounting and routing in later
milestones); here we use `instructor.from_openai` directly for explicit control of
each endpoint and structured-output mode.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import instructor
import openai
from dotenv import load_dotenv
from google import genai

from .config import (
    GEMINI_MODEL,
    GITHUB_MODEL,
    GITHUB_MODELS_ENDPOINT,
    GROQ_ENDPOINT,
    GROQ_MODEL,
)


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    model: str
    env_var: str
    base_url: str | None  # None => Gemini native google-genai client
    mode: instructor.Mode
    multimodal_pdf: bool


PROVIDERS: dict[str, ProviderSpec] = {
    "gemini": ProviderSpec(
        "gemini", GEMINI_MODEL, "GEMINI_API_KEY", None, instructor.Mode.JSON, True
    ),
    "groq": ProviderSpec(
        "groq",
        GROQ_MODEL,
        "GROQ_API_KEY",
        GROQ_ENDPOINT,
        instructor.Mode.TOOLS,  # function-calling (tool-forcing) — reliable on Llama
        False,
    ),
    "github": ProviderSpec(
        "github",
        GITHUB_MODEL,
        "GITHUB_MODELS_TOKEN",
        GITHUB_MODELS_ENDPOINT,
        instructor.Mode.TOOLS,  # OpenAI-compatible function calling
        False,
    ),
}

_genai_raw: genai.Client | None = None
_clients: dict[str, instructor.Instructor] = {}


def _require_key(spec: ProviderSpec) -> str:
    load_dotenv()
    key = os.environ.get(spec.env_var)
    if not key:
        raise RuntimeError(
            f"{spec.env_var} is not set. Add it to .env (see .env.example)."
        )
    return key


def gemini_raw_client() -> genai.Client:
    """Cached raw google-genai client (used for the multimodal PDF path)."""
    global _genai_raw
    if _genai_raw is None:
        _genai_raw = genai.Client(api_key=_require_key(PROVIDERS["gemini"]))
    return _genai_raw


def text_client(provider: str) -> instructor.Instructor:
    """Cached instructor client for a provider's text extraction path."""
    if provider not in PROVIDERS:
        raise ValueError(
            f"Unknown provider {provider!r}. Choose from {sorted(PROVIDERS)}."
        )
    if provider not in _clients:
        spec = PROVIDERS[provider]
        if spec.base_url is None:  # Gemini native
            _clients[provider] = instructor.from_genai(
                gemini_raw_client(), mode=spec.mode
            )
        else:  # OpenAI-compatible (Groq, GitHub Models)
            oai = openai.OpenAI(base_url=spec.base_url, api_key=_require_key(spec))
            _clients[provider] = instructor.from_openai(oai, mode=spec.mode)
    return _clients[provider]
