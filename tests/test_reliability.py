"""Milestone 5: fallback chain, refusal detection, counts.

Deterministic — the provider calls are monkeypatched, so these run offline and
don't touch free-tier quota. (A live end-to-end fallback is demonstrated
separately; see BUILD-LOG.md.)
"""

from __future__ import annotations

import pytest

from resume_extractor import reliability as R
from resume_extractor.schema import Resume


def _fake(behavior: dict[str, object]):
    """Build a fake extract_resume: provider -> "ok" or an Exception to raise."""

    def fake(text: str, provider: str = "gemini") -> Resume:
        outcome = behavior[provider]
        if isinstance(outcome, Exception):
            raise outcome
        return Resume(full_name=f"from {provider}")

    return fake


def test_falls_back_to_second_provider(monkeypatch):
    monkeypatch.setattr(
        R,
        "extract_resume",
        _fake({"gemini": RuntimeError("429 RESOURCE_EXHAUSTED"), "groq": "ok"}),
    )
    res = R.extract_with_fallback("text", providers=("gemini", "groq"))
    assert res.provider == "groq"
    assert res.fallback_count == 1
    assert res.resume.full_name == "from groq"
    assert res.attempts[0].provider == "gemini" and not res.attempts[0].ok


def test_refusal_is_detected_and_triggers_fallback(monkeypatch):
    monkeypatch.setattr(
        R,
        "extract_resume",
        _fake({"gemini": RuntimeError("finish_reason: SAFETY blocked"), "groq": "ok"}),
    )
    res = R.extract_with_fallback("text", providers=("gemini", "groq"))
    assert res.provider == "groq"
    assert res.refusals == 1
    assert res.attempts[0].refused is True


def test_all_providers_failed_raises(monkeypatch):
    monkeypatch.setattr(
        R,
        "extract_resume",
        _fake({"gemini": RuntimeError("boom"), "groq": RuntimeError("boom2")}),
    )
    with pytest.raises(R.AllProvidersFailed):
        R.extract_with_fallback("text", providers=("gemini", "groq"))


def test_first_provider_success_no_fallback(monkeypatch):
    monkeypatch.setattr(R, "extract_resume", _fake({"gemini": "ok"}))
    res = R.extract_with_fallback("text", providers=("gemini", "groq"))
    assert res.provider == "gemini"
    assert res.fallback_count == 0


def test_is_refusal_classifier():
    assert R.is_refusal(RuntimeError("blocked by content_filter"))
    assert R.is_refusal(RuntimeError("finish_reason: SAFETY"))
    assert not R.is_refusal(RuntimeError("connection reset by peer"))
