"""Milestone 8: latency measurement — wall-clock per extraction (METRICS-SPEC §3).

Quota-aware: Groq + GitHub carry the bulk (text extraction over the synthetic set,
repeated for a stable sample); Gemini gets only a couple of timed PDF multimodal
calls (respect ~20/day). Latency needs *fresh* timed calls, so this does NOT use the
accuracy cache. Results are written to `eval/latency.json` and printed; copy the
numbers into BENCHMARK §3.

Usage:
    uv run python eval/latency.py            # Groq + GitHub text latency
    uv run python eval/latency.py --gemini   # + a couple of timed Gemini PDF calls
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

from resume_extractor.extract import extract_resume, extract_resume_from_pdf

ROOT = Path(__file__).parent
TEXTS = sorted((ROOT / "text_resumes").glob("*.txt"))
PDF_DIR = ROOT.parent / "tests" / "sample_resumes"
USE_GEMINI = "--gemini" in sys.argv


def _time(fn) -> float | None:
    start = time.perf_counter()
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        print(f"    skip: {str(exc)[:80]}")
        return None
    return time.perf_counter() - start


def _summary(name: str, samples: list[float]) -> dict | None:
    if not samples:
        print(f"{name:18} no samples (quota/errors)")
        return None
    s = sorted(samples)
    p95 = s[min(len(s) - 1, round(0.95 * (len(s) - 1)))]
    out = {
        "n": len(s),
        "median_s": round(statistics.median(s), 2),
        "p95_s": round(p95, 2),
        "min_s": round(s[0], 2),
        "max_s": round(s[-1], 2),
    }
    print(
        f"{name:18} n={out['n']:2d} median={out['median_s']:.2f}s "
        f"p95={out['p95_s']:.2f}s (min {out['min_s']:.2f} / max {out['max_s']:.2f})"
    )
    return out


def main() -> None:
    results: dict[str, dict | None] = {}

    for provider in ("groq", "github"):
        print(f"\n== {provider} (text, 2 rounds x {len(TEXTS)}) ==")
        samples: list[float] = []
        for _ in range(2):
            for txt in TEXTS:
                text = txt.read_text(encoding="utf-8")
                dt = _time(lambda: extract_resume(text, provider))
                if dt is not None:
                    samples.append(dt)
        results[f"{provider}_text"] = _summary(f"{provider}_text", samples)

    if USE_GEMINI:
        print("\n== gemini (multimodal PDF, 2 calls — quota-limited) ==")
        pdfs = sorted(PDF_DIR.glob("*.pdf"))[:2]
        samples = []
        for pdf in pdfs:
            dt = _time(lambda: extract_resume_from_pdf(pdf))
            if dt is not None:
                samples.append(dt)
        results["gemini_multimodal"] = _summary("gemini_multimodal", samples)
    else:
        print(
            "\n(gemini latency skipped — pass --gemini for a couple of timed PDF calls)"
        )

    (ROOT / "latency.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("\nWrote eval/latency.json")


if __name__ == "__main__":
    main()
