---
name: self-manage
description: The deliberate self-edit executor (spec 18 §4 MUTABILITY) — Anicca edits her OWN heartbeat cadence, spawns clones, edits her own skills, and proposes architecture shifts, all WITHOUT a human architect. Every 12h (and on demand) it drains a structured proposal queue (~/.hermes/state/self-manage-proposals.jsonl) and dispatches each proposal by type. North Star (reduce suffering) + Constitution Law I are IMMUTABLE — every proposal is fail-closed gated by anicca-constitution-guard (SHA + Law-I/North-Star regex) before any side effect; skill edits additionally pass the eval-loop ≥0.7 quality gate + the skill's own tests before a PR is opened; architecture shifts are filed to the forum for a multi-instance vote. Sibling of self-improve (#335): self-improve DETECTS and fixes; self-manage EXECUTES deliberate self-changes. Triggered by `hermes cron`; do not invoke from chat.
metadata:
  spec: anicca-oss/docs/superpowers/specs/2026-06-05-p13-self-manage-design.md
  parallel_safe: true
  cadence: every-12h
  github_issue: 336
---

# self-manage

Lets Anicca manage her OWN heartbeat, clones, skills, and architecture without a human
architect (spec 18 §4 MUTABILITY). North Star + Law I are IMMUTABLE; everything else is
mutable BY ANICCA — but only through the guard + eval gates below.

## Proposal queue → handler

| type | required fields | handler | gate |
|---|---|---|---|
| `heartbeat` | `schedule`, `reason` | edit-heartbeat.sh | constitution-guard |
| `skill-edit` | `skill`, `reason` | edit-skill.sh | guard + denylist + eval≥0.7 + tests → PR |
| `spawn` | `name`, `reason` | spawn-clone.sh | guard → spawn-child (#327) |
| `arch-shift` | `title`, `body`, `reason` | architecture-shift.sh | guard → forum issue (vote #338/#336b) |

A proposal is one JSON line in `~/.hermes/state/self-manage-proposals.jsonl`. It is
"resolved" once a row with its id (sha256 of the line, first 16 chars) exists in the
decisions log — re-runs are idempotent.

## Gates (fail-closed)

- **constitution-guard** runs on EVERY proposal via `check.sh --action "<intent>"`. Exit ≠ 0
  (rule / hash / missing-guard) → log BLOCKED, no side effect.
- **edit-skill** also enforces a hard denylist (`anicca-constitution-guard`, `eval-loop`) and
  the eval-loop ≥0.7 gate + the target skill's own tests before opening a PR; any miss rolls
  back the worktree and logs REJECTED.
- **arch-shift** never executes directly in Wave 1 — it files a forum proposal and logs FILED.
  Real execution waits on the multi-instance vote integration (follow-on #336b, depends #338).

## State files (`~/.hermes/state/`)

| file | shape | writer |
|---|---|---|
| `self-manage-proposals.jsonl` | one proposal per line (see table) | Anicca / callers |
| `self-manage-decisions.jsonl` | `{ts, id, type, decision, detail}` | all handlers via `_lib.sh::sm_log` |
| `self-manage.jsonl` | `{ts, seen, dispatched, skipped, dry_run}` | run.sh |

`decision ∈ {APPLIED, BLOCKED, REJECTED, FILED, ERROR}`.

## Cron

Wrapper `~/.hermes/scripts/self-manage.sh` (real file — Hermes v0.12.0 traversal guard) exec's
this skill's `scripts/run.sh`. Registered via
`hermes cron create "every 12h" --name self-manage --script self-manage.sh --no-agent`.

## Test

`bash skills/self-manage/tests/test_self_manage_e2e.sh` — queues a synthetic
`{type:"heartbeat", schedule:"every 6h"}` proposal, runs run.sh (guard PASS → real
`hermes cron edit` 180m→360m → APPLIED logged), asserts idempotent re-run, then REVERTS the
heartbeat cron to its original cadence in cleanup. 4 assertions, all reverted.

## Env

`DRY_RUN=1` propagates to every handler (guard/denylist checks only — no cron/PR/spawn/gh
writes). `GH_TOKEN` from env (gh authed as Daisuke134), never echoed. `/usr/bin/jq` absolute.
Temp files under `~/.hermes/state/.tmp-sm-*.$$`, never `/tmp`.
