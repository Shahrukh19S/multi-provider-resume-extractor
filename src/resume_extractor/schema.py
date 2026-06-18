"""The extraction schema — the "form" Claude fills in.

Design (BUILD-PLAN.md): every field is optional with a sensible default so a
missing field returns null/empty rather than crashing extraction or forcing a
hallucination. Dates are kept as strings because real resumes are wildly
inconsistent ("2019", "Jan 2019", "Present", "2019–present").

Note on email: we use a plain `str | None` rather than pydantic's `EmailStr`.
Resumes frequently contain lightly-mangled or OCR-damaged emails; rejecting the
whole record over a malformed address would lose otherwise-good data. We capture
what the model returns and can validate/normalize downstream.

Note on `extra`: we deliberately do NOT set `extra="forbid"`. That config emits
`additionalProperties: false` in the JSON schema, which Gemini's native
structured-output `response_schema` rejects (400 INVALID_ARGUMENT). Native
structured outputs already constrain the model to exactly these fields, so it
cannot inject extra keys; pydantic's default (`extra="ignore"`) is the right fit.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Education(BaseModel):
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    start_year: int | None = None
    end_year: int | None = None


class Job(BaseModel):
    company: str
    title: str
    start_date: str | None = None  # free-form; resumes are inconsistent
    end_date: str | None = None  # None / "Present" allowed
    highlights: list[str] = Field(default_factory=list)


class Resume(BaseModel):
    full_name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: list[Job] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
