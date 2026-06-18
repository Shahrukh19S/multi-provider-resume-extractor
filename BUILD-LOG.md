# Build log

Short running log of decisions, deviations, and surprises (feeds the README
"production decision log" and the BRING-BACK-CHECKLIST).

## Milestone 1 — scaffold + schema + sanity

**Environment**
- Python 3.13.6, uv 0.11.19 confirmed present. `uv init --package` produced a
  `src/resume_extractor/` layout and initialized a git repo.
- Installed runtime: anthropic 0.109.2, instructor 1.15.3, litellm 1.89.2,
  openai 2.43.0, pydantic 2.13.4, tenacity 9.1.4, python-dotenv 1.2.2.
  Dev: pytest 9.1.0, ruff 0.15.17.

**Decisions**
- **PDF library deferred to Milestone 3.** SETUP.md §2 lists `pypdf` in the
  install step, but BUILD-PLAN Milestone 3 says to choose the ingestion approach
  during the build (text-extraction vs multimodal, measure the trade-off). Kept
  M1 deps minimal; will add the chosen library at M3.
- **`email` typed as `str | None`, not `EmailStr`.** Real resumes carry mangled /
  OCR-damaged emails; rejecting an entire record over a bad address loses good
  data. Capture as string, validate downstream.
- **`extra="forbid"` on all schema models** so the model can't smuggle in
  hallucinated keys, and so the JSON schema is clean for native structured
  outputs at M2.
- Sanity call uses the official **anthropic SDK directly** (matches SETUP §5).
  The instructor + native-structured-output path is Milestone 2 work.

**Live-docs verification (before writing any provider call)**
- `claude-sonnet-4-6` (primary) and `claude-haiku-4-5-20251001` (cheap): both
  current, both support native structured outputs, both accept `temperature`
  (so `temperature=0` is valid — unlike the Opus 4.7/4.8/Fable tier, which 400
  on sampling params).
- **Surprise / flagged deviation from CLAUDE.md rule #4:** Anthropic now wants
  the *bare alias* for current models — appending a date suffix to an alias 404s.
  So `claude-sonnet-4-6` IS the pinned ID (no dated form exists). Recorded in
  `config.py`.
- OpenAI fallback model intentionally left unset (`config.FALLBACK_MODEL = None`)
  until verified against live OpenAI docs at Milestone 4.

**Open item for review**
- No `ANTHROPIC_API_KEY` present yet, so the live "Claude responds" acceptance
  check is wired but not yet executed. Add a key to `.env` and run
  `uv run pytest` (or `uv run python -m resume_extractor.sanity`) to confirm.

## Provider pivot — Anthropic → free-tier stack (CHANGE-BRIEF.md)

The user has Claude Max but no paid API access; pivoted to build entirely on free
tiers at $0. **Anthropic removed; there is no `ANTHROPIC_API_KEY` and must not be
one.** Stack is now Gemini Flash (primary) → Groq Llama 3.3 70B → GitHub Models
GPT-family. The schema, milestones, and reliability/eval/benchmark design are
unchanged — only provider identities and a few model strings differ.

**Live-docs verification (2026-06-18, before any provider call):**
- **Gemini `gemini-2.5-flash`** — permanent free tier (~1,500 req/day), native
  structured outputs + multimodal PDF. Pinned. (Newer `gemini-3-flash` /
  `3.1-flash-lite` are also free; stuck with 2.5-flash for documented stability.)
- **Groq `llama-3.3-70b-versatile`** — current, NOT deprecated (Groq docs).
  Text-only. Pinned.
- **GitHub Models `openai/gpt-4o-mini`** — free with a PAT (models:read) via the
  OpenAI-compatible endpoint `https://models.github.ai/inference`; that endpoint
  uses publisher-prefixed slugs. To re-confirm the exact slug at Milestone 4.

**Dependency changes:** removed `anthropic`; added `google-genai` (multimodal PDF
+ structured outputs) and `pypdf` (text extraction for text-only providers). Kept
`openai` — it's the OpenAI-compatible client for GitHub Models (M4); we never call
paid OpenAI.

**Milestone 1 re-pointed and CONFIRMED (live):** sanity check now calls Gemini via
the google-genai SDK with `temperature=0`. `uv run python -m resume_extractor.sanity`
→ "hello from gemini". `uv run pytest` → 7 passed (live Gemini test included),
`ruff` clean.

## Milestone 2 — single-provider extraction (Gemini, native structured outputs)

`extract.py`: `extract_resume(text) -> Resume` via `instructor.from_genai` over the
google-genai SDK, `temperature=0`, pinned `gemini-2.5-flash`. Live-confirmed on the
sample resume — every field correct, dates preserved as strings ("Present"), nested
experience/education populated, no hallucination. `uv run pytest` → 8 passed,
`ruff` clean.

**Things that broke / decisions (live-docs surprises):**
- **Native structured outputs needs `jsonref`** — the genai SO path raised a
  ConfigurationError until `uv add "instructor[google-genai]"` (pulls `jsonref`).
- **Gemini `response_schema` rejects `additionalProperties`.** The M1 schema used
  `extra="forbid"`, which emits `additionalProperties:false` → 400 INVALID_ARGUMENT
  from Gemini. Dropped `extra="forbid"`: native SO already constrains output to the
  schema's fields, so the model can't add keys; pydantic default `extra="ignore"`
  is the right fit. Updated the schema test accordingly.
- **`Mode.GENAI_STRUCTURED_OUTPUTS` is deprecated** in instructor (→ v3.0). For the
  GenAI provider, `Mode.JSON` selects the same native-SO handler. Switched to
  `Mode.JSON` (no deprecation warning).
- **Free-tier 429s are real.** Running the sanity + extraction live tests
  back-to-back tripped a transient rate limit. Per CHANGE-BRIEF #6, added a minimal
  `tenacity` retry (exponential backoff + jitter, 5 attempts) scoped to
  rate-limit/quota errors. The full reliability layer (provider fallback chain,
  validation-retry/refusal accounting + counts) remains Milestone 5.

**Chosen mode:** native structured outputs (preferred per rule #2) — not
tool-forcing or plain-prompt JSON.

## Milestone 3 — PDF ingestion (two paths)

`ingest.pdf_to_text()` (pypdf, text-only-provider path) +
`extract.extract_resume_from_pdf()` (Gemini **multimodal**, native `response_schema`)
and `extract.extract_resume_from_pdf_text()` (pypdf → text path). Both confirmed
live on real resume PDFs; `uv run pytest tests/test_pdf_ingestion.py` → 2 passed.
Full suite: 8 passed, 2 skipped→now also covered when PDFs present.

**Verification (rule #3):** confirmed the google-genai PDF API live —
`types.Part.from_bytes(mime_type="application/pdf")` in `contents` +
`config.response_schema=<Pydantic>` → `response.parsed` returns the model. Also
sanity-checked `response_schema=Resume` via a text prompt before wiring the PDF
call.

**Design decision:** the multimodal path calls **google-genai directly** (not
through instructor) — instructor's multimodal genai wrapper isn't cleanly exposed
in 1.15.3, and the direct SDK call is still native structured outputs and fully
controllable. The text path stays on instructor (unification + validation-retries).

**Trade-off (full table in BENCHMARK.md):** multimodal wins on messy/multi-column/
icon-font PDFs (pypdf collapses spacing and leaks icon-font glyphs as fake tokens);
pypdf text is fine & cheaper for clean single-column and is the only path for
text-only providers. Both miss skills rendered as graphics (proficiency bars).

**Things that broke / notes:**
- **Transient 503 UNAVAILABLE** ("high demand") surfaced — the M2 retry only
  matched 429. Broadened the predicate (`_is_transient`) to 429 + 5xx /
  unavailable / overloaded / timeouts (rule #8). Re-ran green.
- **Free-tier RPM 429** when firing ~8 extractions back-to-back — confirms
  CHANGE-BRIEF "don't hammer / batch test runs." Retry helps; spacing calls helps
  more. Full fallback chain is M5.
- **Windows console `UnicodeEncodeError`** printing an emoji (📱) from a resume to
  cp1252 stdout — a *diagnostic-print* issue, not in library code. Flag for the M9
  CLI: force UTF-8 stdout on Windows.
- **Duplicate sample:** `clean_resumes_sample1.pdf` and
  `multi_column_resume_sample1.pdf` are byte-identical (same Byungjin Park resume).
- **Privacy:** `tests/sample_resumes/*.pdf` is git-ignored (real resumes are
  personal data); only the folder README is tracked.

## Milestone 4 — Groq + GitHub Models behind one interface

`providers.py`: a `ProviderSpec` registry + cached client factory. All three
providers go through `instructor`, so `extract.extract_resume(text, provider=...)`
is one signature — swap by name. Confirmed live: Gemini, Groq, and GitHub Models
each extract the same sample correctly.

**Verification (rule #3):** Groq base `https://api.groq.com/openai/v1`, model
`llama-3.3-70b-versatile` is a current production model (not deprecated). GitHub
Models base `https://models.github.ai/inference`, model `openai/gpt-4o-mini`,
OpenAI-compatible; structured outputs supported on gpt-4o-mini+.

**Decisions:**
- **Modes (rule #2):** Gemini uses native structured outputs (`Mode.JSON` →
  `response_schema`). Groq + GitHub Models are wired with `instructor.from_openai`
  in `Mode.TOOLS` (function-calling / tool-forcing) — the sanctioned fallback,
  reliable across both OpenAI-compatible endpoints (Llama's json_schema support is
  uneven; tool-calling is dependable). Recorded in BENCHMARK.md.
- **instructor.from_openai over litellm for dispatch:** chose explicit
  OpenAI-compatible clients (clear base_url + per-provider mode) rather than litellm
  routing. `litellm` stays a dependency for later cost/token accounting (M6) and
  possible Router use; not used for dispatch here. (Minor deviation from SETUP's
  "litellm + instructor" framing — flagged.)
- Text-only providers reuse the M3 pypdf text path for PDFs
  (`extract_resume_from_pdf_text(path, provider=...)`); only Gemini reads PDFs
  directly.

**Tests:** `test_providers.py` parametrizes over all providers (skips per missing
key) + an unknown-provider `ValueError` check (no network).

**Big free-tier finding:** Gemini `gemini-2.5-flash` free tier is **~20 requests
PER DAY** per project (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`,
quotaValue 20) — far below the "1,500/day" figure floating around in blog posts.
Our M1–M4 testing exhausted it, so a full `pytest` run started failing on Gemini
429s. A 30s retry can't clear a *daily* cap.
- **Fix:** live tests now route Gemini/Groq/GitHub calls through
  `tests/live_utils.call_or_skip`, which **skips** (not fails) on transient /
  rate-limit / quota / 5xx errors — correct for a free-tier-dependent suite.
- **Implication:** strongly motivates the Milestone 5 fallback chain (Gemini →
  Groq → GitHub) and "batch test runs, don't hammer." Test Gemini sparingly;
  Groq (~1k/day) and GitHub Models (~50/day) have more headroom.

## Milestone 5 — reliability layer

`reliability.extract_with_fallback(source, providers=("gemini","groq","github"),
is_pdf=...)` walks the chain; each provider call already carries:
- **transport retries** (`tenacity`, exp backoff+jitter, 5 attempts) on 429/5xx/
  timeouts, now logged via `before_sleep_log`;
- **validation-retries** (`instructor max_retries=2`, verified `create` accepts it)
  to re-ask on malformed answers.

On a provider error/refusal it records an `Attempt` and falls back; exposes
`fallback_count` and `refusals`. **Refusal detection** = `is_refusal()` matches
safety/content-block markers; a refusal is a failed attempt, never stored as data.

**Live fallback demo (acceptance):** forced a bad `GEMINI_API_KEY` in-process →
Gemini `401 UNAUTHENTICATED` (non-transient, so no wasted retries) → logged
fallback → **Groq 200 OK** → `Resume(full_name="Jane Doe")`. Counts:
`provider=groq, fallback_count=1, refusals=0` (logged). Auth errors correctly do
NOT trigger transport retries (only 429/5xx/timeouts do).

**Tests:** `test_reliability.py` — fallback-to-second, refusal-triggers-fallback,
all-providers-failed raises, first-success-no-fallback, and the `is_refusal`
classifier. All **monkeypatched / offline** (deterministic, no quota use); the live
fallback was demonstrated via a one-off script (above). `ruff` clean; full
`pytest` → 19 passed.

**Note:** log messages use ASCII (`->`) — an em-dash mojibake'd on the Windows
cp1252 console (cosmetic, same family as the M3 emoji note; M9 CLI will force UTF-8).

## Milestone 6 — caching + cost analysis

`costs.py`: pinned list prices (per 1M tokens, **verified 2026-06-18**), a
normalized `Usage`, `usage_from_completion` (reads Gemini `usage_metadata` and
OpenAI-compatible `usage`), and `cost_usd` / `cost_per_1000`.
`extract.extract_resume_with_usage` uses instructor `create_with_completion` to get
the raw response alongside the model.

**Prices:** Gemini 2.5 Flash $0.30/$2.50 (cached $0.03); Groq llama-3.3-70b
$0.59/$0.79; gpt-4o-mini $0.15/$0.60 (cached $0.075). Sources in `costs.py`.

**Live measurement (one representative resume):** Gemini 176→219 tok = $0.60/1k;
Groq 788→185 = $0.611/1k; GitHub 428→151 = $0.155/1k. Full table in BENCHMARK §2.

**Findings:**
- **Tool-forcing inflates input tokens** — Groq/GitHub (`Mode.TOOLS`) carry the JSON
  function schema in the prompt (Groq 788 input tok) vs Gemini native `response_schema`
  (176). The structured-output *mode* drives token cost as much as the per-token price.
- **gpt-4o-mini cheapest** here despite Gemini's lower input price — resumes are
  output-heavy and Gemini's output ($2.50/M) dominates.
- **Caching ~0 for this workload:** `cached_input_tokens=0` everywhere. The only
  shared prefix is the ~60-token system prompt (below Gemini's implicit-cache
  minimum) and resume bodies are unique. Honest finding per METRICS-SPEC "show the
  token math where [caching] doesn't help"; the code still reads + bills cached
  tokens so a cache-friendly workload would show the saving automatically.

**Tests:** `test_costs.py` — cost math (incl. cached-rate billing), usage
normalization for both response shapes, unreadable-usage raises. Pure/offline.
`ruff` clean; full `pytest` → 25 passed.

**litellm note:** still unused for dispatch; cost accounting was simpler to read
directly from each provider's usage object than to route through litellm. litellm
remains available if a unified cost callback is wanted later.

## Milestone 7 — eval / accuracy

`scoring.py` (pure, unit-tested): normalized scalar match (name/email/phone/
location), set-F1 for skills / companies / institutions, overall = mean.
`eval/run_eval.py`: quota-aware runner — Gemini OFF by default (reserved for the PDF
multimodal comparison), every prediction cached to `eval/cache/` so reruns don't
re-spend quota. Synthetic text set (`eval/text_resumes/` + exact `eval/gold/`,
committed, no PII); real-PDF gold bootstrapped into `eval/gold_pdf/` (git-ignored)
for spot-check.

**Results:**
- **Text set (exact gold): Groq 100%, GitHub 100% (4/4 each)** — trustworthy.
- **Real PDFs: PRELIMINARY** vs bootstrapped gold (github_text ~100% is *circular* —
  GitHub seeded most labels; groq_text ~85%, gemini_multimodal ~80% reflect
  disagreement with unverified labels, not true error). Final numbers await label
  correction in `eval/gold_pdf/`.

**Findings / decisions:**
- **Groq `Mode.TOOLS` → `Mode.JSON`.** Tool-calling intermittently hard-400'd
  ("failed to call a function", not a retryable ValidationError) on some inputs
  (e.g. `syn_d`). `Mode.JSON` is reliable (and rule-#2-preferred). **Cost trade-off:**
  JSON mode injects the schema as prompt text → **2615** input tok vs **788** under
  TOOLS (~3×, $1.94 vs $0.611 / 1k). Kept JSON for reliability; M5 fallback would
  catch a TOOLS failure anyway. BENCHMARK §2 updated to the JSON numbers.
- **GitHub Models has a small free-tier input cap** — the largest PDF
  (`clean_resumes_sample3`) 413'd (`tokens_limit_reached`); Groq's 131k context
  handles it. Bootstrap now seeds via GitHub → Groq → Gemini in order.
- **Synthetic set is the methodological anchor** — exact gold by construction means
  no bootstrap circularity; real PDFs add realism once labels are corrected.

**Tests:** `test_scoring.py` (6, offline). ruff clean.

**Quota note:** spent ~4 Gemini calls (multimodal comparison) + a Groq cost
re-measure this milestone. Reruns without `--gemini` cost zero Gemini.
