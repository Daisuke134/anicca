---
name: aso-loop
description: Weekly App Store Optimization loop for Anicca iOS. Audits the live listing, generates 3 metadata candidates with GPT-5, lints them against Apple character limits + brand guards, and applies them via the asc CLI. Use when the user types /aso-loop, asks "run the ASO loop", or when invoked by a weekly cron. Submits a metadata-only version when needed.
---

# ASO Loop (Anicca iOS)

## When to Use

- User types `/aso-loop` or `/aso-loop --dry-run`
- Weekly OpenClaw cron at Mon 09:00 JST
- User asks "audit my ASO and apply" / "improve App Store metadata"

## App identifiers (locked)

| Field | Value |
|---|---|
| App Store URL | https://apps.apple.com/us/app/daily-affirmations-anicca/id6755129214 |
| App ID | 6755129214 |
| Bundle ID | ai.anicca.app.ios |
| Locales | en-US, ja, de-DE, es-ES, fr-FR, pt-BR |

## Mode flags

- `--dry-run` — generate candidates and post to Slack DM, do not call `asc localizations edit`
- `--locale en-US` — restrict to one locale (default: all 6)
- `--force-submit` — create a new metadata-only version even if no version is currently in PREPARE_FOR_SUBMISSION

## Process

1. **Audit** — invoke `aso-audit` skill on the App Store URL above; capture overall score + per-dimension scores.
2. **Baseline** — run `asc localizations list --version <latest READY or PREPARE>` for each of the 6 locales; cache to `snapshots/$(date +%Y-%m-%d)-baseline-<locale>.json`.
3. **Metric** — run `asc analytics report --metric impressions,product_page_views,conversion_rate --days 7` and capture conversion deltas vs prior week.
4. **Candidate generation** — call OpenAI `gpt-5` (full, NOT mini) with `prompt.md`, audit, baseline, metric, and the contents of https://aniccaai.com/affirmation-app fetched via Firecrawl. Request 3 candidate sets per locale.
5. **Lint** — run `lint.py` on candidates. Reject any that violate:
   - title ≤ 30 chars
   - title MUST contain "anicca" (case-insensitive)
   - title edit distance from current ≤ 5 chars
   - subtitle ≤ 30 chars
   - keywords ≤ 100 chars (single comma-separated string, no spaces)
   - promotional_text ≤ 170 chars
   - no banned-word violations (lint.py owns the list)
6. **Pick** — choose the candidate with the highest `projected_lift_pct`. If 2+ within 5% of top, pick the one with the smallest title edit distance.
7. **Apply** — for each locale: `asc localizations edit --version-id <PREPARE> --locale <X> --name ... --subtitle ... --keywords ... --promotional-text ...`.
8. **Submit if needed** — if no PREPARE version exists, run `asc versions create ... --metadata-only` then submit.
9. **Notify** — slack-automation skill: post before/after diff + audit score + projected lift to {{profile.contact.personalEmail}} Slack DM.
10. **Snapshot** — write applied set to `snapshots/$(date +%Y-%m-%d)-applied.json`.

## Rollback

If the past 3 audit runs all show declining scores, the run aborts the apply step and instead restores the snapshot from 3 weeks ago via `asc localizations edit`. Slack DM is sent.

## Safety

- Major changes (title fully replaced, primary category change) trigger `slack-approval` skill — wait up to 1 hour for user approval, otherwise abort.
- Never modify locales beyond the 6 listed above.
- Never change pricing, IAPs, or non-text assets.
- OpenAI API key must be in `~/.openclaw/.env` as `OPENAI_API_KEY`.
