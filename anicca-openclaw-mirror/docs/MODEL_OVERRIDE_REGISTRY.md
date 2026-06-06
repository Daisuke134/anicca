# MODEL_OVERRIDE_REGISTRY.md

**Source of truth**: `~/.openclaw/openclaw.json::agents.defaults.model`.

This file lists every cron whose `model` field deviates from `defaults`. Each entry MUST justify why frontier/non-default reasoning is needed. Unjustified overrides are deleted on quarterly audit.

**Current defaults (2026-06-06)**:
- `primary`: `openai/gpt-5.4-mini`
- `fallbacks`: `[moonshot/kimi-k2.5, deepseek/deepseek-v4-pro, claude-cli/claude-sonnet-4-6]`

---

## Active overrides

### Sonnet tier (claude-cli/claude-sonnet-4-6 — most expensive, use sparingly)

| Cron ID | Name | Reason | Revisit |
|---|---|---|---|
| `d15ebeb3-0aa9-4d16-9e9a-c177453a96a4` | `anicca-mail-triage` | Mail accuracy is mission-critical: misclassification → wrong reply sent → human/business damage. HARD RULE #6 exception (anicca-inbox owns its own LLM judgment). Verified live 2026-06-04 with sonnet-4-6 successfully drafting + sending real Gmail reply. Downgrade only after 30d of zero misclassification on primary. | 2026-09-06 (3 months) |

### DeepSeek tier (deepseek/deepseek-v4-pro — cheap but strong for long-form reasoning)

| Cron ID | Name | Reason | Revisit |
|---|---|---|---|
| `4cfdfe32-eb9e-47d1-90ea-236ce8757cee` | `anicca-yt-long-en` | YouTube long-form scripting (15-30 min) benefits from frontier-class reasoning to maintain narrative coherence; gpt-5.4-mini insufficient for multi-act structure. deepseek-v4-pro picked over sonnet (1/10 the cost, comparable long-form quality per memory `feedback_crons_use_mini_models_only`). | 2026-09-06 |
| `73d4a8c2-5132-406a-bda3-5508f2d32951` | `anicca-yt-long-ja` | Same as -en; Japanese long-form needs equal reasoning quality. | 2026-09-06 |

---

## Migrated from override → defaults (history, do not re-add)

| Date | Cron ID | Name | From | To | Reason for removing override |
|---|---|---|---|---|---|
| 2026-06-06 | `94c788fe-42d8-4eab-903c-ce991e673013` | `x-buildinpublic-daily` | claude-sonnet-4-6 | defaults (gpt-5.4-mini) | Short X posts (≤280 chars). gpt-5.4-mini quality sufficient for build-in-public format. |
| 2026-06-06 | `ee9c031f-5539-4df4-a39b-246ff933b62a` | `x-engagement-quote` | claude-sonnet-4-6 | defaults (gpt-5.4-mini) | Short engagement quotes. Quality watch: monitor for engagement-rate drop > 25% over 14d; if drop, escalate to deepseek-v4-pro. |

---

## Audit procedure (quarterly)

For each active override:
1. Read the last 7d of cron run logs for the override cron.
2. If 0 failures + Slack confirms output quality acceptable → keep override, push revisit date +90d.
3. If 0 failures + output sometimes wrong/shallow → consider escalating one tier higher.
4. If frequent failures from rate-limit / token cost → consider downgrade or skill restructure.

## Tripwires (immediate action)

- If `~/.openclaw/openclaw.json.last-good` drift detected by `anicca-config-canary` → Slack URGENT, hold all migrations.
- If Anthropic monthly cost > $50 attributable to cron (not chat) → audit sonnet retention; potentially drop mail-triage to deepseek.
- If 14d engagement rate on migrated X posts drops > 25% → consider escalating x-* back to deepseek (NOT sonnet first).
