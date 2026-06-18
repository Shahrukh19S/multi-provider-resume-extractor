"""Prompt / context caching helpers and analysis.

For **this** workload (short, unique resumes) prompt caching yields ~no saving: the
only content shared across calls is the small system prompt — below Gemini's
implicit-cache minimum — and each resume body is unique (see BENCHMARK.md §2). So no
explicit caching is enabled. The pipeline still *reads* cached-token counts from each
response (`costs.usage_from_completion`), so the saving would surface automatically on
a cache-friendly workload (large shared instructions, a RAG corpus, a few-shot bank).

Provider notes:
- **Gemini 2.5 Flash** caches implicitly (no setup) for large reused prefixes, and
  supports explicit context caching (`CachedContent`) — neither helps short resumes.
- **Groq / GitHub Models** (OpenAI-compatible) report cached prompt tokens via
  `usage.prompt_tokens_details.cached_tokens`.

This module exposes a small helper to quantify cache reuse from a `Usage` reading.
"""

from __future__ import annotations

from .costs import Usage


def cache_read_fraction(usage: Usage) -> float:
    """Fraction of input tokens served from cache (0.0 when nothing cached)."""
    if usage.input_tokens <= 0:
        return 0.0
    return usage.cached_input_tokens / usage.input_tokens
