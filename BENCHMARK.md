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
