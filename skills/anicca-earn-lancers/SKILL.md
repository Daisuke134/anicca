---
name: anicca-earn-lancers
description: Daily Lancers gig discovery and apply skill. Camofox (:9377) drives the search, parses up to 15 candidate JIDs, ranks the top 3 by budget vs effort using a mini model (`hermes chat --model gpt-5.2-mini`), and either dry-runs (default — generates proposal text only) or submits via the proven 2-stage Vue-hidden-field pattern (`propose_start → propose_confirm → propose_finish`). LIVE mode requires explicit `--confirm` and is bounded by `--max-apply` + `--max-budget-jpy`. Login uses Google OAuth canonical (`GOOGLE_LOGIN_EMAIL`) via Camofox per HARD RULE; Lancers credentials live in `~/.openclaw/.env`. Cron schedule: daily 10:00 JST (`hermes cron`). Incoming payment routes to the existing OpenClaw bank, which CFO already scrapes — this skill does NOT touch payout. Wave 1 of the earn channel; Coconala + CrowdWorks are Wave 2.
metadata:
  type: earn
  parallel_safe: false
  expected_revenue: ¥3,000–¥50,000 per accepted gig; ~10% accept rate per port-from data
  requires:
    bins: [bash, curl, jq, python3, hermes]
    env: [GOOGLE_LOGIN_EMAIL, GOOGLE_LOGIN_PASSWORD, LANCERS_EMAIL, LANCERS_USERNAME, LANCERS_PASSWORD]
    skills: [camofox-browser]
---

# anicca-earn-lancers

Hermes skill, Wave 1 of the earn channel. Daily cron fires `scripts/run.sh` at 10:00 JST.

## Files
| Path | Role |
|------|------|
| `scripts/run.sh`         | orchestrator (default `--dry-run`) |
| `scripts/login-check.sh` | Camofox session probe + Google OAuth fallback |
| `scripts/scan.sh`        | Camofox search → JID list |
| `scripts/select.sh`      | Mini-model scoring → top 3 |
| `scripts/apply.sh`       | Proposal generation + (with `--confirm`) 2-stage submit |
| `scripts/_lib.sh`        | Shared Camofox REST wrappers + redact + Slack |
| `tests/test_earn_lancers_dry_run.sh` | E2E TDD gate |
| `tests/fixtures/sample-snapshot.json` | offline Camofox snapshot |
| `state/.keep`            | repo placeholder; runtime state lives at `~/.hermes/state/` (X4) |
| `data/.keep`             | repo placeholder; runtime logs live at `~/.hermes/state/` (X4) |
| `~/.hermes/state/earn-lancers-dry-run-latest.json` | last dry-run envelope (overwritable) — runtime |
| `~/.hermes/state/earn-lancers-runs.jsonl` | append-only LIVE submit log — runtime |
| `~/.hermes/state/earn-lancers-cron-fire.log` | transient cron-fire stdout/stderr — runtime |

## Invocation
```bash
# Default (safe)
bash scripts/run.sh --dry-run

# LIVE (Wave 2 only — see docs/superpowers/plans/2026-06-04-earn-lancers-wave2-realsubmit.md)
bash scripts/run.sh --confirm --max-apply 1 --max-budget-jpy 1000
```

## Cron
```
hermes cron create "0 10 * * *" \
  --name anicca-earn-lancers \
  --script ~/.hermes/scripts/anicca-earn-lancers.sh \
  --no-agent
```
The wrapper `~/.hermes/scripts/anicca-earn-lancers.sh` carries the default `--dry-run` semantics — LIVE mode is gated by editing the cron prompt explicitly, never by the daily fire.

## Verify (HARD RULE #14 JOB'S NOT FINISHED)
- E2E test green: `tests/test_earn_lancers_dry_run.sh`
- Hermes cron registered: `hermes cron list | grep anicca-earn-lancers`
- Wave 1 done = scaffold only. `#325` (LAUNCH MATRIX row ④) is NOT closed by this skill alone.
- After a Wave 2 LIVE submit, `tail -1 ~/.hermes/state/earn-lancers-runs.jsonl | jq '.status == "applied"'` must be `true`, the Lancers dashboard URL must show the proposal, AND `cfo-bank` must surface the incoming deposit before `#325` can move.
