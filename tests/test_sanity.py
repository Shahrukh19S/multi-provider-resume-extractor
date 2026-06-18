"""Live connectivity test for Milestone 1 (PRIMARY provider: Gemini).

Skips automatically when GEMINI_API_KEY is absent, so `uv run pytest` stays green
on a fresh clone. With a key in .env it exercises the real Gemini call.
"""

from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv
from live_utils import call_or_skip

from resume_extractor.sanity import hello_gemini

load_dotenv()

requires_key = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set — add it to .env to run the live call",
)


@requires_key
def test_gemini_responds():
    reply = call_or_skip(hello_gemini)
    assert isinstance(reply, str)
    assert reply.strip(), "Gemini returned an empty response"
