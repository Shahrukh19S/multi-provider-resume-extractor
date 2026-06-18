"""Central configuration: pinned model IDs and shared extraction settings.

FREE-TIER STACK (no Anthropic, no paid OpenAI) — see Phase-2-Build-Kit/CLAUDE.md.
Model IDs are the single source of truth (rule #4: pin exact IDs, never "latest").

Verified against live docs on 2026-06-18:
- Gemini 2.5 Flash — permanent free tier (~1,500 req/day), native structured
  outputs + multimodal PDF. ID `gemini-2.5-flash`.
- Groq llama-3.3-70b-versatile — current, NOT deprecated (Groq docs). Text-only.
- GitHub Models GPT-family — `gpt-4o-mini` free with a PAT (models:read), via the
  OpenAI-compatible endpoint https://models.github.ai/inference. On that endpoint
  the catalog uses publisher-prefixed slugs (`openai/gpt-4o-mini`); confirm at M4.
"""

from __future__ import annotations

# --- PRIMARY: Google Gemini (free AI Studio key) -----------------------------
# Native structured outputs + reads PDFs directly (multimodal).
GEMINI_MODEL = "gemini-2.5-flash"

# --- FALLBACK: Groq (free, fast, open) — text-only ---------------------------
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_ENDPOINT = "https://api.groq.com/openai/v1"  # OpenAI-compatible base URL

# --- THIRD: GitHub Models (free w/ PAT) — OpenAI-compatible, text-only --------
GITHUB_MODELS_ENDPOINT = "https://models.github.ai/inference"
# Publisher-prefixed slug for the models.github.ai endpoint. Confirm at Milestone 4.
GITHUB_MODEL = "openai/gpt-4o-mini"

# --- Shared extraction settings ----------------------------------------------
TEMPERATURE = 0  # deterministic extraction (rule #5)

# Provider → env var holding its key (rule #9; ANTHROPIC_API_KEY intentionally absent).
PROVIDER_ENV_VARS = {
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "github": "GITHUB_MODELS_TOKEN",
}
