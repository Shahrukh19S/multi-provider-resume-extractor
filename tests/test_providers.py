"""Milestone 4: one interface over multiple providers.

The same `extract_resume(text, provider=...)` call works for every provider —
parametrized here over all of them. Each case skips if that provider's key is
absent, so the suite stays green with any subset of keys configured.
"""

from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv
from live_utils import call_or_skip

from resume_extractor.extract import extract_resume
from resume_extractor.providers import PROVIDERS
from resume_extractor.schema import Resume

load_dotenv()

SAMPLE = (
    "Jane Doe, jane@x.com. Skills: Python, SQL. "
    "Engineer at Acme 2021-Present. BS Computer Science, MIT, 2016-2020."
)


@pytest.mark.parametrize("provider", sorted(PROVIDERS))
def test_provider_extracts(provider: str):
    spec = PROVIDERS[provider]
    if not os.environ.get(spec.env_var):
        pytest.skip(f"{spec.env_var} not set — add it to .env")
    resume = call_or_skip(extract_resume, SAMPLE, provider=provider)
    assert isinstance(resume, Resume)
    assert "jane" in resume.full_name.lower()


def test_unknown_provider_raises():
    # No network: bad provider name is rejected before any call.
    with pytest.raises(ValueError):
        extract_resume(SAMPLE, provider="nope")
