# P12 Cron Cleanup — Design Spec (2026-06-05)

## Problem

Two cost leaks in the OpenClaw cron fleet:

1. **anicca-event-bot-trigger** (`b781b42e-3c74-4b34-a004-acbcfba3933c`) fires every 15 min, 24h/day, spending a DeepSeek v4-pro LLM call each time even while the operator sleeps. ~24 wasted calls/night (23:30–05:30 = 24 fires).
2. **64 crons in `status=error`** keep retrying on schedule, burning LLM + API budget on doomed runs. Some are dead/superseded and should be disabled.

## Goal

| # | Outcome | Proof |
|---|---------|-------|
| A | event-bot script exits 0 silently (no LLM, no `gog` call) during quiet hours (`profile.alarm.quietHoursStart`..`End`, currently 23:30–05:30 JST) | Run script with a quiet-hours TZ timestamp → exit 0, no `gog`/spawn output |
| B | 64 error crons triaged into `~/.hermes/state/cron-triage.jsonl`, ≤10 confirmed-dead disabled this pass | jsonl row count = error-cron count; `openclaw cron list` shows disabled set; Slack #metrics summary |

## A: quiet-hours skip

**Reuse, don't reinvent.** Canonical guard already exists:
`~/.openclaw/skills/_shared/quiet-hours-guard.sh` — reads `~/.openclaw/identity/profile.json`
`alarm.quietHoursStart`/`End`, `exit 0` if `datetime.now()` (host TZ = Asia/Tokyo, verified)
falls in the cross-midnight window. This is the single source of truth (HARD RULE #16).

Patch: source the guard immediately after `set -euo pipefail`, **before** the `gog calendar`
call, so a quiet-hours fire short-circuits before any LLM/network cost. The cron message text
("If output starts with 'spawning bot'…") is unchanged — when the guard exits 0 the script
produces no stdout, the LLM summarizes "No meeting in window" with no tool calls. Order matters:
the `source` must precede `set -a; . ~/.openclaw/.env` is fine either way, but place guard first
to skip even env-load work.

NOT in scope: per-event override (event-bot only spawns for real meetings; a 01:00 meeting is
rare and the existing `decide`-path in lateness handles critical events separately). Quiet-hours
meetings simply won't auto-spawn a recall bot — acceptable per task ("AND no override → exit 0").

## B: error cron triage

1. `openclaw cron list --json` → filter `status == "error"`.
2. Per cron (bounded to first 30): `openclaw cron logs <id> --tail 50`, parse FIRST distinct error class:

   | signal | category | action |
   |--------|----------|--------|
   | "credentials"/"env not set"/"missing key"/"unauthorized" | infra | leave (retry) |
   | "schema"/"validation"/"ColumnNotFound"/"Invalid request body" | schema_drift | leave (patch later) |
   | "module not found"/"No such file"/"skill removed"/"not executable" | dead | disable |
   | "rate"/"429"/"quota"/"cooldown" | rate_limit | leave |
   | else | unknown | leave |

3. Write one JSONL row per cron to `~/.hermes/state/cron-triage.jsonl`:
   `{id,name,category,first_error,decision,ts}`.
4. Disable `category==dead` (≤10 this pass) via `openclaw cron disable <id>`, EXCEPT the
   protected list (mr-bot core / income / safety — see task brief). Never disable a cron
   I haven't read logs for.
5. Slack #metrics summary + commit script `scripts/cron-cleanup-report.sh` + README + `state/.keep`
   to the worktree.

## Non-goals
- Fixing schema_drift / infra crons (separate pass — only triage + report here).
- Touching runtime state location (stays under `~/.hermes/state` per X4).
