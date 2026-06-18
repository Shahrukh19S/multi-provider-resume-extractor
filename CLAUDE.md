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
  __init__.py     # public exports
  __main__.py     # `python -m resume_extractor` -> CLI
  cli.py          # command-line entry point (the `resume-extractor` command)
  config.py       # pinned model IDs, endpoints, temperature, provider->env-var map
  schema.py       # Pydantic v2 models: Resume / Job / Education (the "form")
  providers.py    # ProviderSpec registry + cached client factory (the one interface)
  ingest.py       # PDF -> text (pypdf) for text-only providers
  extract.py      # extraction calls (text + Gemini multimodal) + transport/validation retries
  reliability.py  # provider fallback chain (Gemini->Groq->GitHub) + refusal detection
  caching.py      # prompt/context-caching analysis + helper
  costs.py        # token usage + hypothetical cost at list prices
  scoring.py      # field-level accuracy scoring (used by the eval harness)
  sanity.py       # one-line Gemini connectivity check
tests/
  data/sample_resume.txt   # text extraction fixture
  sample_resumes/          # PDF fixtures + CREDITS.md (public templates / synthetic)
  live_utils.py            # skip-on-free-tier-limit helper
  test_schema.py test_scoring.py test_costs.py test_reliability.py     # offline
  test_sanity.py test_extraction.py test_pdf_ingestion.py test_providers.py  # live (skip w/o keys)
```

- The **one interface** is `extract.extract_resume(text, provider=...)`, with all
  providers reached through **`instructor`** (`providers.py`). PDFs go to Gemini
  directly (multimodal) or through **`pypdf`** text extraction for text-only providers.
- **Structured-output mode per provider** (rule #2 — prefer native SO, fall back to
  tool-forcing):
  - **Gemini** — native structured outputs via the **google-genai** SDK
    (`Mode.JSON` / `response_schema`); also the only multimodal-PDF path.
  - **Groq** (OpenAI-compatible) — `instructor.from_openai` in **`Mode.JSON`**
    (switched from tool-forcing, which intermittently failed on Llama).
  - **GitHub Models** (OpenAI-compatible) — `instructor.from_openai` in
    **`Mode.TOOLS`** (tool-forcing).
- `litellm` is a dependency but is **not** used for dispatch (kept for possible
  cost/routing use later); dispatch uses `instructor` over each provider's client.

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
