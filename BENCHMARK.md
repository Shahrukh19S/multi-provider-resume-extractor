# BENCHMARK

Metrics captured as the build progresses (see `Phase-2-Build-Kit/METRICS-SPEC.md`).
Tables are scaffolded now and filled in at the relevant milestones — measurement is
not bolted on at the end.

## Pinned models (record the exact IDs used) — free-tier stack, verified 2026-06-18

| Role | Model ID | Structured-output mode (instructor) | Multimodal PDF | temperature=0 |
|---|---|---|---|---|
| Primary (Gemini) | `gemini-2.5-flash` | native SO (`Mode.JSON`, `response_schema`) | yes (direct) | yes |
| Fallback (Groq) | `llama-3.3-70b-versatile` | native JSON (`Mode.JSON`), OpenAI-compat | no (text-only) | yes |
| Third (GitHub Models) | `openai/gpt-4o-mini` | tool-forcing (`Mode.TOOLS`), OpenAI-compat | no (text-only) | yes |

> Groq moved `Mode.TOOLS` → `Mode.JSON` in Milestone 7: tool-calling intermittently
> 400'd ("failed to call a function"); JSON mode is reliable (and rule-#2-preferred),
> at higher token cost — see §2.

All three verified live behind one `extract_resume(text, provider=...)` signature.

> Cost is **hypothetical** — actual spend is $0 on free tiers (see METRICS-SPEC §2).

## Summary — consolidated comparison (Milestone 8)

Accuracy + cost + latency in one view. Spend is **$0**; cost is hypothetical at list
price. Verified by `eval/run_eval.py` + `eval/latency.py`.

| Provider (path) | Text acc (exact gold) | PDF acc (verified gold) | Hyp. cost / 1k | Latency median | Notes |
|---|---|---|---|---|---|
| Gemini (multimodal PDF) | — | **80.4%** (n=4) | $0.60 | _deferred_ | only native PDF path; best on multi-column structure |
| Groq (text) | **100%** (n=4) | **85.4%** (n=4) | $1.94 | **0.67s** | fastest; `Mode.JSON` (reliable, heavier tokens) |
| GitHub Models (text) | **100%** (n=4) | 100%\* (n=3) | **$0.155** | 3.93s | \*gold-seeder → ceiling by construction; cheapest; small input cap |

**Headlines:**
- **100% field accuracy** on clean single-column text (Groq & GitHub, exact gold).
- On real PDFs vs verified gold, **Groq-text 85.4%** vs **Gemini-multimodal 80.4%**
  (text path mildly favored by gold provenance; Gemini wins **companies**, Groq wins
  **skills**).
- **$0 actual cost**; ~**$0.15–1.94 / 1,000 resumes** at list prices.
- **Groq is ~6× faster** than GitHub Models (0.67s vs 3.93s median).
- Survives provider failures via retries + a 3-provider fallback chain.

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

## 1. Accuracy (Milestone 7) — FINAL

Two tracks (harness `eval/run_eval.py`, scorer `resume_extractor.scoring`).

**Text set — synthetic resumes with EXACT gold (cleanest signal):**

| Provider | Mode | full_name | email | phone | location | skills | companies | institutions | Overall | n |
|---|---|---|---|---|---|---|---|---|---|---|
| Groq | `Mode.JSON` | 100% | 100% | 100% | 100% | 100% | 100% | 100% | **100%** | 4 |
| GitHub Models | `Mode.TOOLS` | 100% | 100% | 100% | 100% | 100% | 100% | 100% | **100%** | 4 |

Both nail the clean single-column text case. (Gemini omitted here to conserve its
~20/day quota — it carries the multimodal track below.)

**Real PDFs — scored vs HUMAN-VERIFIED gold:**

| Path | full_name | email | phone | location | skills_f1 | companies_f1 | institutions_f1 | Overall | n |
|---|---|---|---|---|---|---|---|---|---|---|
| github_text | 100% | 100% | 100% | 100% | 100% | 100% | 100% | **100%** | 3 |
| groq_text | 100% | 75% | 100% | 100% | 75% | 73% | 75% | **85.4%** | 4 |
| gemini_multimodal | 100% | 75% | 100% | 75% | 53% | 85% | 75% | **80.4%** | 4 |

> **Honest caveat — gold provenance.** The PDF gold was **seeded by `github_text`,
> then human-verified line-by-line**. So `github_text` scores at ceiling *by
> construction* and shouldn't be read as "best"; and because the gold came from a
> *text-path* extraction, text predictions (`groq_text`) align with it slightly
> more naturally than `multimodal` does. The meaningful read is **`groq_text`
> (85.4%) vs `gemini_multimodal` (80.4%)** against the verified gold — and even that
> carries mild text-path bias. A fully unbiased comparison would need
> independently-authored gold (future work).
>
> **Notable per-field:** `gemini_multimodal` leads on **companies** (85% vs 73%) —
> it reads multi-column layout structure better; `groq_text` leads on **skills**
> (75% vs 53%) — the icon-bar resume (`colored_iconfonts`) renders skills as
> graphics, which the multimodal path under-captures.
>
> **`n` differs:** `github_text` is n=3 — it **cannot process the largest PDF**
> (`clean_resumes_sample3`, 413 `tokens_limit_reached`, small free-tier input cap);
> Groq (131k ctx) and Gemini handle it, so they're n=4.

## 2. Cost (Milestone 6) — hypothetical; actual spend $0

List prices (USD per 1M tokens), **verified 2026-06-18** (pinned in `costs.py`):

| Provider | Model | Input | Output | Cached input |
|---|---|---|---|---|
| Gemini | gemini-2.5-flash | $0.30 | $2.50 | $0.03 |
| Groq | llama-3.3-70b-versatile | $0.59 | $0.79 | n/a (no cache discount) |
| GitHub Models | openai/gpt-4o-mini | $0.15 | $0.60 | $0.075 |

Measured on one representative resume (`temperature=0`):

| Provider | SO mode | Input tok | Output tok | Cached | $/resume | $/1,000 |
|---|---|---|---|---|---|---|
| Gemini | native `response_schema` | 176 | 219 | 0 | $0.000600 | **$0.60** |
| Groq | `Mode.JSON` | 2615 | 498 | 0 | $0.001936 | **$1.94** |
| GitHub Models | `Mode.TOOLS` | 428 | 151 | 0 | $0.000155 | **$0.155** |

**Findings — the structured-output *mode* dominates input-token cost:**
- **Gemini native `response_schema` is by far the leanest input** (**176** tok) — the
  schema is enforced by the API and **not** billed as prompt.
- **GitHub `Mode.TOOLS`** carries the schema as a compact function definition (**428**).
- **Groq `Mode.JSON`** injects the full JSON schema *as prompt text* and emits more
  verbose output → **2615** in / 498 out, ~3× the tokens of its old `Mode.TOOLS` run
  (788/185). **Reliability-vs-cost trade-off:** we accept the higher token cost for
  JSON mode's reliability (tool-calling hard-400'd on some inputs); the M5 fallback
  would catch a tool-calling failure regardless.
- **gpt-4o-mini is cheapest** hypothetically (~$0.155/1k) — low per-token price +
  compact tool schema. Gemini's output price ($2.50/M) makes it pricier despite the
  lean input.
- Actual paid cost: **$0** (all free tiers).

### Caching analysis (why it's ~0 for this workload)

`cached_input_tokens` was **0** on every provider. For resume extraction the only
shared prefix across calls is the system prompt (~60 tokens) and each resume body is
unique — far below Gemini's implicit-cache minimum (≈1,024+ tokens for Flash) and
with nothing else to reuse. **Prompt caching pays off with a large shared context
(long instructions, RAG corpus, few-shot bank), not short unique resumes.** The
plumbing reads `cached_input_tokens` and bills it at each provider's cached rate, so
the saving would show automatically in a workload that *can* cache.

## 3. Latency (Milestone 8)

Wall-clock per extraction (`eval/latency.py`); text path on the synthetic set,
2 rounds × 4 = 8 samples each.

| Provider | Model | Path | Median | p95 | min / max | n |
|---|---|---|---|---|---|---|
| Groq | llama-3.3-70b-versatile | text | **0.67s** | 2.25s | 0.60 / 2.25 | 8 |
| GitHub Models | openai/gpt-4o-mini | text | 3.93s | 4.96s | 2.94 / 4.96 | 8 |
| Gemini | gemini-2.5-flash | multimodal PDF | _deferred_ | — | — | 0 |

- **Groq is ~6× faster than GitHub Models** (0.67s vs 3.93s median) — its headline
  speed advantage (custom inference hardware), making it the natural workhorse.
- **Gemini latency deferred:** the ~20/day free quota was exhausted by the day's
  accuracy + cost runs, so timed PDF calls 429'd. Re-run `uv run python
  eval/latency.py --gemini` on a fresh quota day to fill this row.

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

- Runs at **$0** on free tiers; **would cost ~$0.15–1.94 per 1,000 resumes** at list
  prices (gpt-4o-mini cheapest; Groq priciest because JSON mode carries the schema
  in-prompt).
- Caching saving is **~0% for this workload** — resumes are short and unique;
  caching is a scale-with-shared-context lever, not a resume-extraction one.
- **100% field accuracy (Groq & GitHub) on the synthetic exact-gold text set**;
  on real PDFs (verified gold) Groq-text 85.4% vs Gemini-multimodal 80.4%.
- **Groq is ~6× faster** than GitHub Models (0.67s vs 3.93s median per extraction).
- Survives provider failures via transport + validation retries and a 3-provider
  fallback chain.
