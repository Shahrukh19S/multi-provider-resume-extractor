# eval/ — Milestone 7 accuracy harness

Field-level accuracy per provider, **quota-aware** (Gemini is ~20 req/day).

## Layout

| Path | Committed? | What |
|---|---|---|
| `text_resumes/*.txt` | ✅ yes | Synthetic single-column resumes (no PII) |
| `gold/*.json` | ✅ yes | **Exact** gold labels for the synthetic set |
| `gold_pdf/*.json` | ✗ git-ignored | **Bootstrapped** labels for real PDFs — spot-check & correct these |
| `cache/*.json` | ✗ git-ignored | Cached predictions (so reruns don't re-spend quota) |
| `REPORT.md` | ✗ git-ignored | Generated report (may reference real resumes) |

## Run

```bash
uv run python eval/run_eval.py            # Groq + GitHub on the text set (no Gemini)
uv run python eval/run_eval.py --gemini   # + Gemini multimodal PDF comparison
```

- **Gemini is OFF by default** — reserved for the PDF multimodal comparison. Do
  iterative runs without `--gemini`.
- **Every prediction is cached** to `eval/cache/`; delete a file to recompute one.
- Scoring lives in `resume_extractor.scoring` (pure, unit-tested).

## Bootstrap-label workflow

1. Run the harness — it seeds `gold_pdf/*.json` from a cheap provider.
2. **Spot-check and correct** those JSON files against the real PDFs.
3. Re-run — predictions are cached, so only scoring recomputes, now against your
   corrected gold → true per-provider/per-path accuracy.
