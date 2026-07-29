# cron-cleanup (P12)

Cost-saver pass over the OpenClaw cron fleet. Two pieces.

## A. event-bot quiet-hours skip

`anicca-event-bot-trigger` (UUID `b781b42e-3c74-4b34-a004-acbcfba3933c`) fires
every 15 min, 24h/day. During the operator's quiet hours (`profile.alarm.quietHoursStart`
..`quietHoursEnd`, currently `23:30–05:30` JST) the meeting scanner has no reason to
run — it just burns a DeepSeek call + a `gog calendar` round-trip each fire (~24/night).

**Fix:** `$LIFE_MANAGER_REPO/skills/anicca-meeting-attendant/scripts/check-and-spawn.sh` now
sources the canonical guard `$LIFE_MANAGER_REPO/skills/_shared/quiet-hours-guard.sh`
immediately after `set -euo pipefail`, before env-load and the `gog` call. The guard
reads the live profile window and `exit 0` silently when `datetime.now()` (host TZ =
Asia/Tokyo) falls inside it. No new quiet-hours logic was added — single source of truth.

Verified: at 00:58 JST (inside window) the patched script exits 0 with empty stdout
(no `gog`, no LLM); guard logic returns `quiet=0` for a window that excludes "now".

## B. error-cron audit

`scripts/cron-cleanup-report.sh` pulls `openclaw cron list --all --json`, filters
`state.lastStatus == "error"`, and categorizes each from the gateway's inline
`state.lastDiagnostics.summary` (last fire's stderr / model-router result) — no
per-cron `openclaw cron logs` round-trip needed. Output: `~/.hermes/state/cron-triage.jsonl`
(one row per error cron: `id, name, enabled, category, protected, consecutiveErrors,
first_error, decision, ts`).

### Pass result (2026-06-05)

| category | count | meaning | action |
|----------|-------|---------|--------|
| rate_limit | 38 | provider cooldown / billing (DeepSeek, Codex, Moonshot "in cooldown" / "usage limit") | leave — fuel/billing issue, not the cron |
| unknown | 25 | gateway-restart blip, LLM idle timeout, agent setup timeout, single transient fail | leave — `consecutiveErrors` low, not dead |
| schema_drift | 2 | `Invalid request body` (`anicca-recruit-comedy-weekly`, `anicca-x-promote-monthly`) | leave — needs a patch, not disable |
| infra | 0 | — | — |
| **dead** | **0** | missing module / file / removed skill | **none to disable** |

**0 crons disabled.** No genuinely-dead cron exists: every error is transient
(provider cooldown, restart, timeout) and almost all are on the `cron-protect.txt`
list (income / content / safety / life-manager core). Disabling per the
"only if confirmed truly dead, else leave for human review" rule = disable nothing.
The 64-error count is dominated by the documented multi-provider cooldown cascade —
a budget/fuel problem to fix in the model-router, not by culling crons.

Two unprotected error crons are already `enabled=false` (`anicca-universal-observer`,
`anicca-x-promote-monthly`), so no further action.

### Re-run

```bash
bash scripts/cron-cleanup-report.sh   # rewrites ~/.hermes/state/cron-triage.jsonl
```

Runtime state (`cron-triage.jsonl`) lives under `~/.hermes/state` per repo convention X4;
only the script + this README are committed here.
