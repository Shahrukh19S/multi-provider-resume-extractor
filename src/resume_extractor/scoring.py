"""Milestone 7: field-level accuracy scoring (predicted vs gold Resume).

Pure functions, no network. Metrics (METRICS-SPEC §1):
- **Scalar fields** (full_name, email, phone, location): normalized exact match
  (lowercase, whitespace-collapsed). `summary` is excluded — it's free-form prose
  with no single correct value.
- **List fields** as set F1: `skills`, experience `companies`, education
  `institutions` — these legitimately over/under-extract, so precision/recall/F1
  is the right lens.
- **Overall** = mean of the per-field scores (scalars as 1/0, lists as F1).
"""

from __future__ import annotations

from dataclasses import dataclass

from .schema import Resume

SCALAR_FIELDS = ("full_name", "email", "phone", "location")


def _norm(value: str | None) -> str:
    return " ".join((value or "").lower().split())


def _set_f1(pred_items: list[str], gold_items: list[str]) -> float:
    pred = {_norm(x) for x in pred_items if _norm(x)}
    gold = {_norm(x) for x in gold_items if _norm(x)}
    if not pred and not gold:
        return 1.0  # both empty == agreement
    tp = len(pred & gold)
    precision = tp / len(pred) if pred else 0.0
    recall = tp / len(gold) if gold else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


@dataclass
class FieldScores:
    scalar: dict[str, bool]
    skills_f1: float
    companies_f1: float
    institutions_f1: float

    def as_dict(self) -> dict[str, float]:
        d: dict[str, float] = {k: float(v) for k, v in self.scalar.items()}
        d["skills_f1"] = self.skills_f1
        d["companies_f1"] = self.companies_f1
        d["institutions_f1"] = self.institutions_f1
        return d

    @property
    def overall(self) -> float:
        vals = list(self.as_dict().values())
        return sum(vals) / len(vals)


def score(pred: Resume, gold: Resume) -> FieldScores:
    """Score one predicted Resume against the gold Resume."""
    scalar = {
        f: _norm(getattr(pred, f)) == _norm(getattr(gold, f)) for f in SCALAR_FIELDS
    }
    return FieldScores(
        scalar=scalar,
        skills_f1=_set_f1(pred.skills, gold.skills),
        companies_f1=_set_f1(
            [j.company for j in pred.experience], [j.company for j in gold.experience]
        ),
        institutions_f1=_set_f1(
            [e.institution for e in pred.education],
            [e.institution for e in gold.education],
        ),
    )


def aggregate(scores: list[FieldScores]) -> dict[str, float]:
    """Mean of each field metric (and overall) across a set of scored resumes."""
    if not scores:
        return {}
    keys = list(scores[0].as_dict().keys())
    agg = {k: sum(s.as_dict()[k] for s in scores) / len(scores) for k in keys}
    agg["overall"] = sum(s.overall for s in scores) / len(scores)
    return agg
