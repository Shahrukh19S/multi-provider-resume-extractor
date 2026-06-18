"""Milestone 2: Gemini extraction on a known sample resume.

Live test — skips without GEMINI_API_KEY. Assertions are tolerant of phrasing
(the model may normalize text) but pin the unambiguous facts in the sample.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from resume_extractor.extract import extract_resume
from resume_extractor.schema import Resume

load_dotenv()

requires_key = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set — add it to .env to run the live extraction",
)

SAMPLE = (Path(__file__).parent / "data" / "sample_resume.txt").read_text(
    encoding="utf-8"
)


@requires_key
def test_extracts_known_sample():
    resume = extract_resume(SAMPLE)

    assert isinstance(resume, Resume)

    # Identity / contact — unambiguous in the source text.
    assert "Jane" in resume.full_name and "Doe" in resume.full_name
    assert resume.email == "jane.doe@example.com"

    # List fields populated, not hallucinated empty.
    assert any("python" in s.lower() for s in resume.skills)

    companies = {job.company.lower() for job in resume.experience}
    assert any("acme" in c for c in companies)
    assert len(resume.experience) >= 2

    institutions = {edu.institution.lower() for edu in resume.education}
    assert any("berkeley" in i for i in institutions)
