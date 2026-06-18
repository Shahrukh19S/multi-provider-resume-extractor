"""Milestone 6: token accounting + hypothetical cost analysis.

Actual spend is **$0** (free tiers). We read token usage from each provider's
response and compute what the same workload *would* cost at each provider's
published list price — the "ran it free, here's the bill at scale" portfolio
artifact (METRICS-SPEC §2). Prices are pinned with the date they were verified.

On caching: for resume extraction the only shared prefix across calls is the small
system prompt (~tens of tokens) — far below Gemini's implicit-cache minimum — and
each resume body is unique, so prompt caching yields ~0 savings for *this* workload.
We surface `cached_input_tokens` from usage so the effect is measurable, and note
that caching pays off only with a large shared context (not short, unique resumes).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Published list prices, USD per 1,000,000 tokens. Verified 2026-06-18.
# Sources: ai.google.dev/gemini-api/docs/pricing (Gemini 2.5 Flash),
# groq.com/pricing (Llama 3.3 70B Versatile), OpenAI list for gpt-4o-mini.
PRICE_DATE = "2026-06-18"
PRICES: dict[str, dict[str, float]] = {
    "gemini": {"input": 0.30, "output": 2.50, "cached_input": 0.03},
    "groq": {"input": 0.59, "output": 0.79, "cached_input": 0.59},  # no cache discount
    "github": {
        "input": 0.15,
        "output": 0.60,
        "cached_input": 0.075,
    },  # gpt-4o-mini list
}


@dataclass
class Usage:
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0  # subset of input_tokens served from cache

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


def usage_from_completion(provider: str, completion: Any) -> Usage:
    """Normalize a provider's raw usage into a common `Usage`.

    Gemini (google-genai) reports `usage_metadata`; OpenAI-compatible providers
    (Groq, GitHub Models) report `usage`.
    """
    meta = getattr(completion, "usage_metadata", None)
    if meta is not None:  # Gemini
        return Usage(
            input_tokens=getattr(meta, "prompt_token_count", 0) or 0,
            output_tokens=getattr(meta, "candidates_token_count", 0) or 0,
            cached_input_tokens=getattr(meta, "cached_content_token_count", 0) or 0,
        )

    usage = getattr(completion, "usage", None)
    if usage is not None:  # OpenAI-compatible
        details = getattr(usage, "prompt_tokens_details", None)
        cached = (getattr(details, "cached_tokens", 0) or 0) if details else 0
        return Usage(
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            cached_input_tokens=cached,
        )

    raise ValueError(f"could not read token usage from {provider} response")


def cost_usd(provider: str, usage: Usage) -> float:
    """Hypothetical cost (USD) for one extraction at `provider`'s list price.

    Cached input tokens are billed at the cached rate; the rest at the input rate.
    """
    price = PRICES[provider]
    uncached_input = max(usage.input_tokens - usage.cached_input_tokens, 0)
    return (
        uncached_input / 1_000_000 * price["input"]
        + usage.cached_input_tokens / 1_000_000 * price["cached_input"]
        + usage.output_tokens / 1_000_000 * price["output"]
    )


def cost_per_1000(provider: str, usage: Usage) -> float:
    """Projected hypothetical cost for 1,000 resumes of this size."""
    return cost_usd(provider, usage) * 1000
