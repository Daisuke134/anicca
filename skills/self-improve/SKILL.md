---
name: self-improve
description: The per-instance self-improvement loop (spec 18 §1) — the unsolved core of autonomy. Every 6h Anicca builds a self-model (meta-cognition.sh reads heartbeat/eval-cost/constitution-violations/wallet/cfo + cron error count), detects what is broken or slop (detect.sh: slop-detected/law-violation/cron-degraded/income-stalled/report-broken), files a GitHub issue on Daisuke134/anicca-oss with an @anicca mention (file-issue.sh, dedup per type per day), attempts an autonomous symphony-style fix in an isolated worktree gated by the eval-loop ≥0.7 + the skill's own tests (attempt-fix.sh), opens a PR, and shares the learning to learnings.jsonl + the source issue so ALL instances benefit (share-learning.sh). North Star (reduce suffering) + Law I are IMMUTABLE and never auto-edited. Triggered ONLY by `hermes cron`; do not invoke from chat.
metadata:
  spec: anicca-oss/docs/superpowers/specs/2026-06-05-p10-self-improve-design.md
  parallel_safe: true
  cadence: every-6h
  github_issue: 335
---

# self-improve

The loop that lets Anicca manage, monitor, and improve its OWN everything without a human
architect (spec 18 §1). Runs THROUGH GitHub Issues so the swarm shares one brain (§2).

## Loop

```
meta-cognition.sh  → ONE self-state JSON (finances, activity, health, identity)
detect.sh          → JSONL of detected issues (5 rules below)
file-issue.sh      → gh issue create (@anicca) per NEW issue, dedup per (type, day)
attempt-fix.sh     → isolate worktree → hermes chat edit → eval≥0.7 + tests → PR
share-learning.sh  → append learnings.jsonl + comment + close source issue
run.sh             → orchestrate all of the above, idempotent
```

## Detection rules (detect.sh)

| issue_type | condition | severity |
|---|---|---|
| slop-detected | any eval-cost row `pass:false` within 24h | warn |
| law-violation | any constitution-violations row `decision != OK` within 24h | critical |
| cron-degraded | cron error count > 10 | warn |
| income-stalled | wallet 0 USDC AND lifeline != THRIVE | info |
| report-broken | daily-report newest row > 24h stale | warn |

## Mutability guard

North Star (reduce suffering) + Constitution Law I are IMMUTABLE. `attempt-fix.sh` refuses to
edit `CONSTITUTION.md` / the constitution-guard / any "North Star" target and instead comments
on the issue requesting human review. Everything else (skills, config, cron, architecture) is
self-mutable per spec 18 §4.

## State files (`~/.hermes/state/`)

| file | shape | writer |
|---|---|---|
| `self-improve.jsonl` | `{ts, detected, filed, fixed, dry_run}` | run.sh |
| `self-improve-filed.jsonl` | `{ts, issue_type, day, issue_number, title, url}` | file-issue.sh |
| `learnings.jsonl` | `{ts, issue, pr, category, insight}` | share-learning.sh |

## Cron

Wrapper `~/.hermes/scripts/self-improve.sh` (real file — Hermes v0.12.0 traversal guard) exec's
this skill's `scripts/run.sh`. Registered via
`hermes cron create "every 6h" --name self-improve --script self-improve.sh --no-agent`.

## Test

`bash skills/self-improve/tests/test_self_improve_e2e.sh` — synthetic fake `pass:false` eval row
→ detect emits slop-detected → file-issue DRY prints the title → exit 0.

## Env

`DRY_RUN=1` propagates to every step (no gh/worktree/hermes writes). `GH_TOKEN` from env (gh
authed as Daisuke134), never echoed. `/usr/bin/jq` absolute. Temp files under
`~/.hermes/state/.tmp-*.$$`, never `/tmp`.
