# BENCHMARK

Metrics captured as the build progresses (see `Phase-2-Build-Kit/METRICS-SPEC.md`).
Tables are scaffolded now and filled in at the relevant milestones — measurement is
not bolted on at the end.

## Pinned models (record the exact IDs used) — free-tier stack, verified 2026-06-18

| Role | Model ID | Structured outputs | Multimodal PDF | temperature=0 |
|---|---|---|---|---|
| Primary (Gemini) | `gemini-2.5-flash` | native | yes (direct) | yes |
| Fallback (Groq) | `llama-3.3-70b-versatile` | via instructor | no (text-only) | yes |
| Third (GitHub Models) | `openai/gpt-4o-mini` | native (OpenAI-compatible) | no (text-only) | yes |

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

## 2. Cost (Milestone 6)

| Setting | Cost/resume | Notes |
|---|---|---|
| Caching OFF | _TBD_ | baseline |
| Caching ON (1h TTL) | _TBD_ | ~__% cheaper |

Prices + date used: _record at Milestone 6._

## 3. Latency (Milestone 7)

| Provider | Model | Median | p95 |
|---|---|---|---|
| Gemini | gemini-2.5-flash | _TBD_ | _TBD_ |
| Groq | llama-3.3-70b-versatile | _TBD_ | _TBD_ |
| GitHub Models | openai/gpt-4o-mini | _TBD_ | _TBD_ |

## 4. Reliability (Milestone 5)

Transport retries / validation-retries / fallback activations / refusals: _TBD_.

## Headline numbers (for README + docs)

- Extracts a resume for **$_TBD_**.
- Caching cut cost by **_TBD_%**.
- **_TBD_%** field accuracy (Claude), **_TBD_%** (fallback).
- Survives provider failures via retries + fallback.
