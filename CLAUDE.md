# CLAUDE.md

Project context for Claude Code working in this repository.

## What this is

**resume-extractor** — a typed, multi-provider LLM client and CLI that reads messy
real-world resumes/CVs and returns clean, schema-validated structured data
(name, contact, skills, work history with dates, education) through **one
interface** over several providers, with retries and provider fallback.

Cost is **$0**: the project runs entirely on provider **free tiers**, and reports
cost as a hypothetical analysis at published list prices.

## Provider stack (free tiers only)

| Role | Pinned model ID | Notes |
|---|---|---|
| **Primary** | `gemini-2.5-flash` | native structured outputs + multimodal PDF |
| **Fallback** | `llama-3.3-70b-versatile` (Groq) | fast, text-only |
| **Third** | `openai/gpt-4o-mini` (GitHub Models) | OpenAI-compatible `https://models.github.ai/inference`; text-only |

Model IDs are pinned in `src/resume_extractor/config.py` (single source of truth).

## Architecture

```
src/resume_extractor/
  config.py    # pinned model IDs + shared settings (temperature, provider→env-var map)
  schema.py    # Pydantic v2 models: Resume / Job / Education (the extraction "form")
  sanity.py    # one-line connectivity check against Gemini
  extract.py   # extract_resume(text) -> Resume via instructor + Gemini native SO
  __init__.py  # public exports: Resume, Job, Education, extract_resume
tests/
  data/sample_resume.txt   # extraction fixture
  test_schema.py           # schema validation (no network)
  test_sanity.py           # live Gemini hello (skips without GEMINI_API_KEY)
  test_extraction.py       # live extraction on the fixture (skips without key)
```

- Structured output goes through **`instructor`** over the **google-genai** SDK in
  `Mode.JSON` (Gemini's native `response_schema` path).
- `litellm` + `instructor` provide the unified interface for the OpenAI-compatible
  fallbacks (Groq, GitHub Models). `pypdf` handles PDF text for text-only providers.

## Build / test / quality commands

```bash
uv sync                                   # install deps into .venv
cp .env.example .env                       # then add your free keys
uv run python -m resume_extractor.sanity   # live Gemini "hello"
uv run pytest                              # schema tests + live tests (skip w/o keys)
uv run ruff check . && uv run ruff format . # lint + format (run before any commit)
```

Run `ruff check` and `ruff format` before considering any change done.

## Engineering rules (project constraints)

1. **Free tiers only.** No Anthropic, no paid OpenAI. There must be **no
   `ANTHROPIC_API_KEY`**. Respect free rate limits (batch test runs; don't hammer).
2. **Prefer native structured outputs**, then tool-forcing, then plain-prompt JSON
   as a last resort. Use `instructor` to unify this across providers.
3. **Verify model IDs against live docs** before writing provider calls — they drift.
4. **Pin exact model IDs**, never "latest"; record them in `config.py`. (Gemini's
   current models use a bare alias — appending a date suffix 404s.)
5. **temperature = 0** for all extraction calls (determinism).
6. **PDF by provider type:** send PDFs directly to Gemini (multimodal); extract text
   first (pypdf) for text-only providers.
7. **Reliability:** `tenacity` transport retries (free-tier 429s are common),
   `instructor` validation-retries, and a provider fallback chain. Detect refusals;
   never store a refusal as data.
8. **Secrets hygiene:** keys live in `.env` (git-ignored); commit only `.env.example`.
   Never commit real keys.

## Notes for contributors

- The live tests make real Gemini calls and **skip automatically** when
  `GEMINI_API_KEY` is unset, so a fresh clone's `pytest` stays green offline.
- Keep a short running build log in `BUILD-LOG.md`; capture metrics in `BENCHMARK.md`.
