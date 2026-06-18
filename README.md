# resume-extractor

Typed multi-provider LLM client + resume extractor. Reads messy real-world
resumes/CVs and returns clean, schema-validated structured data via one interface
over a **free-tier provider stack** — with validation-retries, transport retries,
provider fallback, and (where supported) context caching. Runs at **$0**; cost is
reported as a hypothetical analysis at published list prices.

> **Status:** Phase 2 build in progress. **Milestones 1–8 complete** (scaffold +
> schema + Gemini sanity; Gemini extraction via native structured outputs; PDF
> ingestion — multimodal + text; multi-provider — Gemini/Groq/GitHub Models behind
> one interface; reliability — retries + validation-retries + provider fallback
> chain; token accounting + hypothetical cost analysis; eval/accuracy harness;
> benchmark write-up). See `BENCHMARK.md` and `Phase-2-Build-Kit/BUILD-PLAN.md`.

## Provider stack (free tiers only — no Anthropic, no paid OpenAI)

| Role | Model ID (pinned) | Notes |
|---|---|---|
| **Primary** | `gemini-2.5-flash` | native structured outputs + multimodal PDF; `temperature=0` |
| **Fallback** | `llama-3.3-70b-versatile` (Groq) | fast, text-only |
| **Third** | `openai/gpt-4o-mini` (GitHub Models) | OpenAI-compatible `https://models.github.ai/inference`; text-only |

## Setup

```bash
uv sync                       # install deps into an isolated venv
cp .env.example .env          # then paste your free keys into .env
```

`.env` holds `GEMINI_API_KEY`, `GROQ_API_KEY`, `GITHUB_MODELS_TOKEN` and is
git-ignored. There is intentionally **no** `ANTHROPIC_API_KEY`.

## Run the Milestone 1 sanity check

```bash
uv run python -m resume_extractor.sanity   # one-line "hello" call to Gemini
uv run pytest                              # schema tests + live Gemini test (skips w/o key)
uv run ruff check . && uv run ruff format --check .
```

## Extract a resume from text (Milestone 2)

```python
from resume_extractor import extract_resume

resume = extract_resume(open("resume.txt").read())
print(resume.full_name, resume.skills)
```

Uses Gemini native structured outputs (`temperature=0`), validates into the
`Resume` pydantic model, and retries on transient errors (429/5xx).

**Swap providers with the same call (Milestone 4):**

```python
extract_resume(text, provider="gemini")  # default — native structured outputs
extract_resume(text, provider="groq")    # llama-3.3-70b-versatile (text-only)
extract_resume(text, provider="github")  # openai/gpt-4o-mini (text-only)
```

## Reliability — retries + fallback chain (Milestone 5)

```python
from resume_extractor import extract_with_fallback

# Tries Gemini -> Groq -> GitHub Models; each call already does transport retries
# (429/5xx) and instructor validation-retries. A provider that errors or refuses
# is skipped; a refusal is never stored as data.
result = extract_with_fallback(text)                 # or is_pdf=True with a path
print(result.provider, result.fallback_count, result.refusals)
resume = result.resume
```

## Cost analysis (Milestone 6 — hypothetical; spend is $0)

```python
from resume_extractor import extract_resume_with_usage, usage_from_completion, cost_usd

resume, completion = extract_resume_with_usage(text, provider="github")
usage = usage_from_completion("github", completion)
print(usage.input_tokens, usage.output_tokens, cost_usd("github", usage))
```

List prices are pinned in `costs.py` (verified 2026-06-18). Measured ~**$0.15–0.61
per 1,000 resumes** depending on provider; see `BENCHMARK.md`.

## Extract from a PDF (Milestone 3)

```python
from resume_extractor import extract_resume_from_pdf, extract_resume_from_pdf_text

# Gemini multimodal — send the PDF directly (best for messy/multi-column layouts)
resume = extract_resume_from_pdf("resume.pdf")

# Text path — pypdf text extraction, then extract (what text-only providers use)
resume = extract_resume_from_pdf_text("resume.pdf")
```
