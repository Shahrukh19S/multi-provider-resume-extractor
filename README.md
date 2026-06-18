# resume-extractor

Typed multi-provider LLM client + resume extractor. Reads messy real-world
resumes/CVs and returns clean, schema-validated structured data via one interface
over a **free-tier provider stack** — with validation-retries, transport retries,
provider fallback, and (where supported) context caching. Runs at **$0**; cost is
reported as a hypothetical analysis at published list prices.

> **Status:** Phase 2 build in progress. **Milestones 1–2 complete** (scaffold +
> schema + Gemini sanity; single-provider extraction via Gemini native structured
> outputs). See `Phase-2-Build-Kit/BUILD-PLAN.md`.

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
`Resume` pydantic model, and retries on free-tier rate limits. PDF input lands in
Milestone 3.
