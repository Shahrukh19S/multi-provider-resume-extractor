"""Milestone 6: cost math + usage normalization (pure, no network)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from resume_extractor import costs
from resume_extractor.costs import Usage


def test_cost_usd_input_and_output():
    u = Usage(input_tokens=1_000_000, output_tokens=1_000_000)
    # gemini: $0.30 input + $2.50 output per 1M
    assert costs.cost_usd("gemini", u) == pytest.approx(0.30 + 2.50)


def test_cached_input_billed_at_cached_rate():
    u = Usage(input_tokens=1_000_000, output_tokens=0, cached_input_tokens=1_000_000)
    assert costs.cost_usd("gemini", u) == pytest.approx(0.03)  # all cached


def test_cost_per_1000_scales():
    u = Usage(input_tokens=200, output_tokens=150)
    assert costs.cost_per_1000("github", u) == pytest.approx(
        costs.cost_usd("github", u) * 1000
    )


def test_usage_from_gemini_metadata():
    comp = SimpleNamespace(
        usage_metadata=SimpleNamespace(
            prompt_token_count=176,
            candidates_token_count=219,
            cached_content_token_count=10,
        )
    )
    u = costs.usage_from_completion("gemini", comp)
    assert (u.input_tokens, u.output_tokens, u.cached_input_tokens) == (176, 219, 10)


def test_usage_from_openai_usage():
    comp = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=428,
            completion_tokens=151,
            prompt_tokens_details=SimpleNamespace(cached_tokens=5),
        )
    )
    u = costs.usage_from_completion("github", comp)
    assert (u.input_tokens, u.output_tokens, u.cached_input_tokens) == (428, 151, 5)


def test_usage_unreadable_raises():
    with pytest.raises(ValueError):
        costs.usage_from_completion("groq", SimpleNamespace())
