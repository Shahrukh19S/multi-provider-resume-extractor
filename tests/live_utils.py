"""Helpers for live (network) tests.

Free tiers impose real and sometimes tiny quotas (e.g. Gemini 2.5 Flash is ~20
requests/day on the free tier). When a live call hits a rate limit / quota / 5xx,
that's an external condition, not a code defect — so we **skip** the test rather
than fail it. Non-transient errors still propagate.
"""

from __future__ import annotations

from typing import Any, Callable

import pytest

from resume_extractor.extract import _is_transient


def call_or_skip(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run a live call; skip the test on free-tier rate-limit/quota/5xx errors."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 — intentionally broad; re-raised below
        if _is_transient(exc):
            pytest.skip(f"provider free-tier limit / transient: {str(exc)[:140]}")
        raise
