"""Milestone 7 eval runner — field-level accuracy per provider, quota-aware.

Design (per the quota guidance):
- **Gemini is scarce (~20/day)** → OFF by default. Pass `--gemini` to enable the
  PDF multimodal comparison + any image-only bootstrap. Groq/GitHub are the
  workhorses for iterative runs.
- **Every prediction is cached to `eval/cache/`** keyed by (item, provider, mode);
  a rerun reads cache and never re-spends quota. Delete a cache file to recompute.
- **Gold labels:** synthetic set in `eval/gold/` (exact, committed). Real-PDF gold
  is *bootstrapped* into `eval/gold_pdf/` (seed via GitHub text, or Gemini multimodal
  for non-text PDFs) for you to spot-check/correct before final scoring.

Usage:
    uv run python eval/run_eval.py            # Groq + GitHub on text set (no Gemini)
    uv run python eval/run_eval.py --gemini   # + Gemini multimodal PDF comparison
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from resume_extractor.extract import (
    _is_transient,
    extract_resume,
    extract_resume_from_pdf,
)
from resume_extractor.ingest import pdf_to_text
from resume_extractor.schema import Resume
from resume_extractor.scoring import FieldScores, aggregate, score

ROOT = Path(__file__).parent
CACHE = ROOT / "cache"
GOLD = ROOT / "gold"
GOLD_PDF = ROOT / "gold_pdf"
TEXT_DIR = ROOT / "text_resumes"
PDF_DIR = ROOT.parent / "tests" / "sample_resumes"

TEXT_PROVIDERS = ("groq", "github")  # workhorses — safe to rerun

USE_GEMINI = "--gemini" in sys.argv


def _load_gold(path: Path) -> Resume:
    return Resume.model_validate_json(path.read_text(encoding="utf-8"))


def _cached(key: str, fn: Callable[[], Resume]) -> Resume | None:
    """Return a cached prediction, else compute+cache it. None on transient error."""
    CACHE.mkdir(exist_ok=True)
    f = CACHE / f"{key}.json"
    if f.exists():
        return _load_gold(f)
    try:
        result = fn()
    except Exception as exc:  # noqa: BLE001
        kind = "transient/quota" if _is_transient(exc) else "error"
        print(f"  ! {key}: {kind}: {str(exc)[:90]}")
        return None
    f.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result


def _pct(x: float) -> str:
    return f"{x * 100:5.1f}%"


def _report_block(title: str, per_provider: dict[str, list[FieldScores]]) -> str:
    lines = [f"### {title}", ""]
    if not any(per_provider.values()):
        return "\n".join(lines + ["_no results_", ""])
    fields = [
        "full_name",
        "email",
        "phone",
        "location",
        "skills_f1",
        "companies_f1",
        "institutions_f1",
        "overall",
    ]
    lines.append("| Provider | " + " | ".join(fields) + " | n |")
    lines.append("|" + "---|" * (len(fields) + 2))
    for prov, scores in per_provider.items():
        if not scores:
            lines.append(f"| {prov} | " + " | ".join(["—"] * len(fields)) + " | 0 |")
            continue
        agg = aggregate(scores)
        row = " | ".join(_pct(agg[f]) for f in fields)
        lines.append(f"| {prov} | {row} | {len(scores)} |")
    lines.append("")
    return "\n".join(lines)


def run_text_set() -> dict[str, list[FieldScores]]:
    """Synthetic text resumes vs exact gold — trustworthy numbers."""
    items = sorted(TEXT_DIR.glob("*.txt"))
    per_provider: dict[str, list[FieldScores]] = {p: [] for p in TEXT_PROVIDERS}
    print(f"\n== TEXT set ({len(items)} synthetic resumes) ==")
    for txt in items:
        gold = _load_gold(GOLD / f"{txt.stem}.json")
        text = txt.read_text(encoding="utf-8")
        for prov in TEXT_PROVIDERS:
            pred = _cached(
                f"{txt.stem}__{prov}__text", lambda: extract_resume(text, prov)
            )
            if pred is None:
                continue
            s = score(pred, gold)
            per_provider[prov].append(s)
            print(f"  {txt.stem:8} {prov:7} overall={_pct(s.overall)}")
    return per_provider


def bootstrap_pdf_gold() -> list[Path]:
    """Seed gold labels for real PDFs (for spot-check). Returns PDFs with gold."""
    GOLD_PDF.mkdir(exist_ok=True)
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    ready: list[Path] = []
    print(f"\n== Bootstrap gold for {len(pdfs)} real PDFs ==")
    for pdf in pdfs:
        gold_path = GOLD_PDF / f"{pdf.stem}.json"
        if gold_path.exists():
            ready.append(pdf)
            continue
        # Prefer cheap text seeding (GitHub small cap → Groq 131k for big docs);
        # fall back to Gemini multimodal for non-text / image-only PDFs.
        seed: Resume | None = None
        try:
            text = pdf_to_text(pdf)
            for seed_prov in ("github", "groq"):
                seed = _cached(
                    f"{pdf.stem}__{seed_prov}__seed",
                    lambda: extract_resume(text, seed_prov),
                )
                if seed is not None:
                    break
        except ValueError:
            text = None
        if seed is None and USE_GEMINI:
            seed = _cached(
                f"{pdf.stem}__gemini__seed", lambda: extract_resume_from_pdf(pdf)
            )
        if seed is None:
            print(
                f"  ! {pdf.stem}: could not seed (text-only failed; rerun with --gemini)"
            )
            continue
        gold_path.write_text(seed.model_dump_json(indent=2), encoding="utf-8")
        print(f"  seeded {pdf.stem} -> eval/gold_pdf/{pdf.stem}.json  (SPOT-CHECK ME)")
        ready.append(pdf)
    return ready


def run_pdf_comparison(pdfs: list[Path]) -> dict[str, list[FieldScores]]:
    """Multimodal (Gemini) vs text (Groq/GitHub) on real PDFs, vs bootstrapped gold."""
    labels = ["gemini_multimodal", "groq_text", "github_text"]
    per: dict[str, list[FieldScores]] = {k: [] for k in labels}
    print("\n== PDF comparison (vs bootstrapped gold — preliminary) ==")
    for pdf in pdfs:
        gold_path = GOLD_PDF / f"{pdf.stem}.json"
        if not gold_path.exists():
            continue
        gold = _load_gold(gold_path)
        # text paths
        try:
            text = pdf_to_text(pdf)
        except ValueError:
            text = None
        if text is not None:
            for prov, label in (("groq", "groq_text"), ("github", "github_text")):
                pred = _cached(
                    f"{pdf.stem}__{prov}__text", lambda: extract_resume(text, prov)
                )
                if pred is not None:
                    per[label].append(score(pred, gold))
        # multimodal (reserved Gemini)
        if USE_GEMINI:
            pred = _cached(
                f"{pdf.stem}__gemini__multimodal", lambda: extract_resume_from_pdf(pdf)
            )
            if pred is not None:
                per["gemini_multimodal"].append(score(pred, gold))
    return per


def main() -> None:
    print(f"Gemini enabled: {USE_GEMINI}")
    text_scores = run_text_set()
    pdfs = bootstrap_pdf_gold()
    pdf_scores = run_pdf_comparison(pdfs)

    report = "\n".join(
        [
            "# Eval report (Milestone 7)",
            "",
            "> Text set = synthetic resumes with **exact** gold (trustworthy).",
            "> PDF section is **preliminary** — scored vs *bootstrapped* gold awaiting",
            "> spot-check/correction in `eval/gold_pdf/`.",
            "",
            _report_block(
                "Text set — field accuracy per provider (exact gold)", text_scores
            ),
            _report_block("Real PDFs — preliminary (vs bootstrapped gold)", pdf_scores),
        ]
    )
    (ROOT / "REPORT.md").write_text(report, encoding="utf-8")
    print("\nWrote eval/REPORT.md")
    print("\n" + report)


if __name__ == "__main__":
    main()
