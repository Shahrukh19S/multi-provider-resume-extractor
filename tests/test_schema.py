"""Schema validation tests (BUILD-PLAN Milestone 1)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from resume_extractor.schema import Education, Job, Resume


def test_minimal_resume_only_requires_full_name():
    r = Resume(full_name="Ada Lovelace")
    assert r.full_name == "Ada Lovelace"
    # Optional fields default to None / empty, not missing — so a sparse resume
    # never crashes extraction.
    assert r.email is None
    assert r.skills == []
    assert r.experience == []
    assert r.education == []


def test_full_name_is_required():
    with pytest.raises(ValidationError):
        Resume()  # type: ignore[call-arg]


def test_nested_job_and_education_parse():
    r = Resume(
        full_name="Grace Hopper",
        skills=["COBOL", "compilers"],
        experience=[
            Job(
                company="US Navy",
                title="Rear Admiral",
                start_date="1943",
                end_date="Present",
                highlights=["Coined the term 'debugging'"],
            )
        ],
        education=[Education(institution="Yale", degree="PhD", end_year=1934)],
    )
    assert r.experience[0].company == "US Navy"
    assert r.experience[0].highlights == ["Coined the term 'debugging'"]
    assert r.education[0].end_year == 1934


def test_dates_are_strings_not_coerced():
    job = Job(company="Acme", title="Engineer", end_date="Present")
    assert job.end_date == "Present"


def test_extra_fields_ignored():
    # We intentionally don't use extra="forbid" — it emits additionalProperties,
    # which Gemini's native structured-output response_schema rejects. Unknown
    # keys are ignored, and native SO prevents the model emitting them anyway.
    r = Resume(full_name="X", made_up_field="oops")  # type: ignore[call-arg]
    assert not hasattr(r, "made_up_field")


def test_schema_is_json_serializable():
    # Native structured outputs (Milestone 2) need a clean JSON schema.
    schema = Resume.model_json_schema()
    assert schema["type"] == "object"
    assert "full_name" in schema["properties"]
