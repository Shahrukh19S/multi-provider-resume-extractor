# BENCHMARK

Metrics captured as the build progresses (see `Phase-2-Build-Kit/METRICS-SPEC.md`).
Tables are scaffolded now and filled in at the relevant milestones — measurement is
not bolted on at the end.

## Pinned models (record the exact IDs used) — free-tier stack, verified 2026-06-18

| Role | Model ID | Structured-output mode (instructor) | Multimodal PDF | temperature=0 |
|---|---|---|---|---|
| Primary (Gemini) | `gemini-2.5-flash` | native SO (`Mode.JSON`, `response_schema`) | yes (direct) | yes |
| Fallback (Groq) | `llama-3.3-70b-versatile` | tool-forcing (`Mode.TOOLS`), OpenAI-compat | no (text-only) | yes |
| Third (GitHub Models) | `openai/gpt-4o-mini` | tool-forcing (`Mode.TOOLS`), OpenAI-compat | no (text-only) | yes |

All three verified live behind one `extract_resume(text, provider=...)` signature.

> Cost is **hypothetical** — actual spend is $0 on free tiers (see METRICS-SPEC §2).

## PDF ingestion trade-off (Milestone 3)

Two ingestion paths: **Gemini multimodal** (send the PDF directly) vs. **pypdf
text extraction** (flatten to text, then extract — the path text-only providers
must use). Observed on the sample set (field *counts*, not graded accuracy — that's
Milestone 7):

| Resume (layout) | pypdf text quality | Text-path result | Multimodal result | Takeaway |
|---|---|---|---|---|
| MARY SMITH (clean, 1-col) | clean (9.3k chars) | name✓, skills 3, exp 3, edu 1 | identical | **tie** — text path is fine & cheaper |
| Byungjin Park (multi-col, icon-font) | **mangled**: collapsed spaces (`DevOpsEngineer`), icon glyphs leak as words (`HOUSE-CHIMNEY`, `GITHUB-SQUARE`, 📱) | degraded input | name✓, exp 8, edu 1, **skills 0** | **multimodal wins** on layout; but skills shown as visual bars were missed by *both* |
| Debarghya Das (2-col) | flattened but legible (3.3k chars) | name✓, skills 17, exp 6, edu 3 | (not measured — hit 429) | LLM recovers structure from flattened 2-col text |

**Conclusions (decision log):**
- **Default to Gemini multimodal for messy / multi-column / icon-font PDFs** — it
  preserves reading order and doesn't leak icon-font glyphs that pypdf turns into
  fake "skills"/tokens.
- **pypdf text is adequate (and cheaper) for clean single-column** resumes, and is
  the **only** path for text-only providers (Groq, GitHub Models) in M4.
- **Caveat both ways:** pypdf collapses spacing / leaks glyph names; multimodal can
  miss info rendered as *graphics* (proficiency bars → `skills: []`). A skills-bar
  resume is a known hard case for both.
- Token usage + hypothetical $ per path: deferred to Milestone 6.

## 1. Accuracy (Milestone 7)

| Provider | Model | Overall field-acc | Notable per-field |
|---|---|---|---|
| Gemini (primary) | gemini-2.5-flash | _TBD_ | _TBD_ |
| Groq (fallback) | llama-3.3-70b-versatile | _TBD_ | _TBD_ |
| GitHub Models | openai/gpt-4o-mini | _TBD_ | _TBD_ |

## 2. Cost (Milestone 6) — hypothetical; actual spend $0

List prices (USD per 1M tokens), **verified 2026-06-18** (pinned in `costs.py`):

| Provider | Model | Input | Output | Cached input |
|---|---|---|---|---|
| Gemini | gemini-2.5-flash | $0.30 | $2.50 | $0.03 |
| Groq | llama-3.3-70b-versatile | $0.59 | $0.79 | n/a (no cache discount) |
| GitHub Models | openai/gpt-4o-mini | $0.15 | $0.60 | $0.075 |

Measured on one representative resume (`temperature=0`):

| Provider | Input tok | Output tok | Cached | $/resume | $/1,000 |
|---|---|---|---|---|---|
| Gemini | 176 | 219 | 0 | $0.000600 | **$0.60** |
| Groq | 788 | 185 | 0 | $0.000611 | **$0.611** |
| GitHub Models | 428 | 151 | 0 | $0.000155 | **$0.155** |

**Findings:**
- **Tool-forcing inflates input tokens.** Groq/GitHub use `Mode.TOOLS`, which puts
  the full JSON function schema in the prompt → Groq counts **788** input tokens vs
  Gemini's **176** (native `response_schema`, schema not billed as prompt). A direct
  per-token comparison must account for this, not just the headline $/M price.
- **gpt-4o-mini is cheapest** hypothetically here (~$0.155/1k), despite Gemini's
  lower input price, because Gemini's output is pricier ($2.50/M) and resumes are
  output-heavy (structured JSON).
- Actual paid cost: **$0** (all free tiers).

### Caching analysis (why it's ~0 for this workload)

`cached_input_tokens` was **0** on every provider. For resume extraction the only
shared prefix across calls is the system prompt (~60 tokens) and each resume body is
unique — far below Gemini's implicit-cache minimum (≈1,024+ tokens for Flash) and
with nothing else to reuse. **Prompt caching pays off with a large shared context
(long instructions, RAG corpus, few-shot bank), not short unique resumes.** The
plumbing reads `cached_input_tokens` and bills it at each provider's cached rate, so
the saving would show automatically in a workload that *can* cache.

## 3. Latency (Milestone 7)

| Provider | Model | Median | p95 |
|---|---|---|---|
| Gemini | gemini-2.5-flash | _TBD_ | _TBD_ |
| Groq | llama-3.3-70b-versatile | _TBD_ | _TBD_ |
| GitHub Models | openai/gpt-4o-mini | _TBD_ | _TBD_ |

## 4. Reliability (Milestone 5)

Mechanisms wired and observed:
- **Transport retries** (`tenacity`, exp backoff + jitter, 5 attempts, logged) on
  429/5xx/timeouts — observed riding out live Gemini `503 UNAVAILABLE` and `429`.
- **Validation-retries** (`instructor max_retries=2`) — re-asks on malformed output.
- **Provider fallback chain** Gemini → Groq → GitHub Models via
  `extract_with_fallback`, with per-attempt records (`fallback_count`, `refusals`).
- **Refusal detection** — safety/content-block errors are classified and treated as
  a failed attempt (never stored as data), triggering fallback.

Live fallback demo (forced bad Gemini key → fall back):

| Step | Provider | Outcome |
|---|---|---|
| 1 | gemini | **401 UNAUTHENTICATED** (non-transient → no wasted retries) → fall back |
| 2 | groq | **200 OK** → `Resume(full_name="Jane Doe")` |

Result: `provider=groq, fallback_count=1, refusals=0` — counts logged.

## Headline numbers (for README + docs)

- Runs at **$0** on free tiers; **would cost ~$0.15–0.61 per 1,000 resumes** at
  list prices (gpt-4o-mini cheapest, Groq priciest here).
- Caching saving is **~0% for this workload** — resumes are short and unique;
  caching is a scale-with-shared-context lever, not a resume-extraction one.
- **_TBD_% / _TBD_% / _TBD_%** field accuracy (Gemini / Groq / GitHub) — Milestone 7.
- Survives provider failures via transport + validation retries and a 3-provider
  fallback chain.
