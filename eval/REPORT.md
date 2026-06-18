# Eval report (Milestone 7)

> Text set = synthetic resumes with **exact** gold (trustworthy).
> PDF section is **preliminary** — scored vs *bootstrapped* gold awaiting
> spot-check/correction in `eval/gold_pdf/`.

### Text set — field accuracy per provider (exact gold)

| Provider | full_name | email | phone | location | skills_f1 | companies_f1 | institutions_f1 | overall | n |
|---|---|---|---|---|---|---|---|---|---|
| groq | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 4 |
| github | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 4 |

### Real PDFs — preliminary (vs bootstrapped gold)

| Provider | full_name | email | phone | location | skills_f1 | companies_f1 | institutions_f1 | overall | n |
|---|---|---|---|---|---|---|---|---|---|
| gemini_multimodal | 100.0% |  75.0% | 100.0% |  75.0% |  53.4% |  84.6% |  75.0% |  80.4% | 4 |
| groq_text | 100.0% |  75.0% | 100.0% | 100.0% |  75.0% |  73.1% |  75.0% |  85.4% | 4 |
| github_text | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 3 |
