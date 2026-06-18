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

Two tracks (see `eval/run_eval.py`, report in `eval/REPORT.md`):

**Text set — synthetic resumes with EXACT gold (trustworthy):**

| Provider | Mode | Overall field-acc | n | Notes |
|---|---|---|---|---|
| Groq | `Mode.JSON` | **100%** | 4 | all fields exact after the JSON-mode switch |
| GitHub Models | `Mode.TOOLS` | **100%** | 4 | all fields exact |

(Gemini omitted from the text track to conserve its ~20/day quota; it carries the
multimodal-PDF track instead.)

**Real PDFs — PRELIMINARY, scored vs *bootstrapped* gold (awaiting spot-check):**

| Path | Overall | n | Caveat |
|---|---|---|---|
| github_text | ~100% | 3 | **circular** — GitHub seeded most gold labels |
| groq_text | ~85% | 4 | disagreement with GitHub-seeded gold, not true error |
| gemini_multimodal | ~80% | 4 | likewise; also `skills` 53% (icon-bar resume) |

These PDF numbers are **not** final accuracy — they measure agreement with
unverified bootstrap labels. After the labels in `eval/gold_pdf/` are corrected,
re-running scores true per-path accuracy. **GitHub Models cannot process the largest
PDF** (`clean_resumes_sample3`) — 413 `tokens_limit_reached` (small free-tier input
cap); Groq (131k ctx) handles it.

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

- Runs at **$0** on free tiers; **would cost ~$0.15–1.94 per 1,000 resumes** at list
  prices (gpt-4o-mini cheapest; Groq priciest because JSON mode carries the schema
  in-prompt).
- Caching saving is **~0% for this workload** — resumes are short and unique;
  caching is a scale-with-shared-context lever, not a resume-extraction one.
- **100% field accuracy (Groq & GitHub) on the synthetic exact-gold text set**;
  real-PDF accuracy pending label spot-check.
- Survives provider failures via transport + validation retries and a 3-provider
  fallback chain.
