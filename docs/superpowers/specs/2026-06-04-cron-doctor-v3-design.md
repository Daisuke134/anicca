# Spec v3: cron-doctor + credit observability — out-of-scope R-tasks

| meta | value |
|---|---|
| parent | `2026-06-04-cron-doctor-v2-design.md` |
| scope | R-1, R-2, R-3, R-10, R-12 (previously out-of-scope, now in per /goal hook) |
| out of scope | R-5 (doctor handles nightly, no impl needed) |
| date | 2026-06-04 22:30 JST |
| directive | /goal: "implement end-to-end. run. fix. re-run. push." |

## 1. What v3 adds

| R | gap | impl |
|---|---|---|
| R-1 | OpenAI credit/spend monitor | new skill `anicca-credit-monitor` + OpenClaw cron daily 09:00 JST → Slack |
| R-2 | Anthropic + DeepSeek credit refill detection | same skill checks all 3 providers; doctor L3 also detects 401/credit errors in cron output |
| R-3 | 24h natural-fire observation auto-verify | doctor new L8 phase: scan `state.lastRunAtMs` of watched crons vs expected interval; alert/refire if stale |
| R-10 | OpenClaw upstream PR docs | 3 markdown issue drafts in `~/anicca-project/docs/issues/` |
| R-12 | CFO sync helper | new helper `cfo_sync.py` reads `~/.openclaw/skills/cfo-core/data/` and reconciles `revenue-critical.json` monthly |

## 2. Design

### 2.1 anicca-credit-monitor (R-1 + R-2)

```
~/.openclaw/skills/anicca-credit-monitor/
├── SKILL.md
└── scripts/
    └── check.sh         # probes OpenAI + Anthropic + DeepSeek balance/usage,
                         # posts unified Slack report
```

`check.sh` behavior:
- Reads `~/.openclaw/.env` (provider API keys) + `~/.codex/auth.json` (canonical OpenAI key fallback).
- For each provider, sends a 1-token probe (`/v1/models` GET).
  - 200 OK → "alive"
  - 401/403 + body contains "Incorrect API key" → "auth_broken"
  - 429 + body contains "rate" → "rate_limited"
  - 402 / "insufficient" / "credit" → "credit_low"
- Reads doctor's `data/openai-spend.json` for current-month spend.
- Posts Slack `:moneybag:` line per provider + total spend summary.

New cron: `anicca-credit-monitor`, `0 9 * * *` Asia/Tokyo, isolated, `--no-deliver`, message = wrapper bash to `check.sh`.

### 2.2 doctor L8 phase — last-fire watchdog (R-3)

`phases.py::phase_l8_last_fire_watchdog(jobs, watched_set, max_age_hours)`:
- For each cron in `watched_set` (= revenue-critical.json + cron-doctor itself + credit-monitor):
  - Compute age_hours = `(now - state.lastRunAtMs) / 3600000`
  - Compute expected_interval_hours = parse cron expression (e.g. `0 */6 * * *` → 6h)
  - If age > 2× expected → flag as "stale"
  - If flagged: `_refire(cron_id)` + record in report
- Returns `{stale: [...], refired: [...], count: N}`

L8 added to phases.py main() + format_report.py.

### 2.3 doctor L3 extension — multi-provider credit detector (R-2)

`phases.py::REFUSAL_PATTERNS` extended with:
- `401\s+Unauthorized`
- `insufficient.{0,20}credit`
- `credit.{0,20}exhausted`
- `429.{0,20}rate.limit`

When L3 detects these patterns in Slack history, the matching cron is re-fired (rate-limited as before) AND a `:warning:` Slack post tags `@channel` with `provider_credit_alert`.

### 2.4 cfo_sync (R-12)

`helpers/cfo_sync.py::reconcile()`:
- Reads `~/.openclaw/skills/cfo-core/data/cancelled-overrides.json` if present.
- Reads `revenue-critical.json`.
- For each revenue-critical cron, checks Stripe revenue (via `cfo-core` if available).
- If mismatch (= cron in revenue-critical but Stripe shows $0 last 30d) → report.
- Pure read; never mutates revenue-critical.json. Slack posts `:chart:` summary.

Invoked as a new monthly OpenClaw cron `anicca-cfo-sync`, `0 5 1 * *` Asia/Tokyo (1st of month 05:00 JST).

### 2.5 R-10 upstream PR drafts

3 markdown files under `~/anicca-project/docs/issues/`:
- `openclaw-payload-model-ignored.md` — bug + repro + fix proposal
- `openclaw-refusal-classified-as-success.md` — same
- `openclaw-jobs-json-hot-reload-race.md` — same

Each follows GitHub issue template: Summary / Repro / Expected / Actual / Proposed fix / Repro logs path.

## 3. Verification matrix

| AC | check |
|---|---|
| V-1 | `anicca-credit-monitor` cron registered + `openclaw cron run` fires + Slack `:moneybag:` line per provider |
| V-2 | doctor L3 regex includes 4 new credit patterns; unit test added |
| V-3 | doctor L8 phase runs; if a watched cron has age > 2× interval, refire happens |
| V-4 | `cfo_sync.reconcile()` returns dict; called manually + Slack `:chart:` posted |
| V-5 | 3 issue drafts exist; each has Repro section |
| V-6 | end-to-end: doctor run prints L1/L2/L3/L4/L5/L7/L8 keys; auto-commit triggers if dirty |
| V-7 | E2E run #2 (immediately after #1) → idempotent (no new commits, no refire of recently-refired) |

## 4. Out-of-scope (v3 strict)

- Actual Anthropic/DeepSeek balance refill (= Dais's wallet action) — only detection
- OpenClaw repo PR submission (= manual via `gh pr create` separately)
- Mutating revenue-critical.json from CFO (= read-only)
