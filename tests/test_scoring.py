"""Milestone 7: scoring engine (pure, offline)."""

from __future__ import annotations

import pytest

from resume_extractor.schema import Job, Resume
from resume_extractor.scoring import aggregate, score


def _resume(**kw) -> Resume:
    return Resume(**kw)


def test_perfect_match_scores_one():
    r = _resume(
        full_name="Jane Doe",
        email="jane@x.com",
        skills=["Python", "SQL"],
        experience=[Job(company="Acme", title="Engineer")],
    )
    s = score(r, r)
    assert s.overall == pytest.approx(1.0)


def test_scalar_normalization():
    pred = _resume(full_name="  JANE   DOE ")
    gold = _resume(full_name="Jane Doe")
    s = score(pred, gold)
    assert s.scalar["full_name"] is True


def test_skills_set_f1_partial():
    pred = _resume(full_name="x", skills=["Python", "SQL"])
    gold = _resume(full_name="x", skills=["python", "go"])
    # overlap {python}; precision 1/2, recall 1/2 -> F1 0.5
    assert score(pred, gold).skills_f1 == pytest.approx(0.5)


def test_both_empty_lists_agree():
    pred = _resume(full_name="x")
    gold = _resume(full_name="x")
    s = score(pred, gold)
    assert s.skills_f1 == 1.0 and s.companies_f1 == 1.0 and s.institutions_f1 == 1.0


def test_mismatched_scalar_is_false():
    s = score(_resume(full_name="A"), _resume(full_name="B"))
    assert s.scalar["full_name"] is False


def test_aggregate_means():
    a = score(_resume(full_name="A"), _resume(full_name="A"))  # overall 1.0
    b = score(_resume(full_name="A"), _resume(full_name="B"))  # full_name wrong
    agg = aggregate([a, b])
    assert 0.0 < agg["overall"] < 1.0
    assert agg["full_name"] == pytest.approx(0.5)
