---
name: daily-report
description: Sends a USEFUL daily Anicca digest (yesterday's CFO numbers, heartbeat health, constitution-violations, friction-fixer errors, 3 LLM-synthesized substantive bullets) from anicca-genesis@agentmail.to to ANICCA_REPORT_TO every day at 06:00 JST. Reads ~/.openclaw/skills/cfo-core/data/anicca-cfo.json + ~/.hermes/state/heartbeat.jsonl + ~/.openclaw/skills/anicca-friction-fixer/state/violations.jsonl + ~/.openclaw/state/friction-sweep.log. Triggered ONLY by `hermes cron`; do not invoke from chat.
metadata:
  spec: anicca-oss/docs/superpowers/plans/2026-06-04-daily-report.md
  parallel_safe: true
  cadence: daily-06:00-JST
  user-invocable: false
  requires:
    bins: [bash, jq, python3]
    env: [AGENTMAIL_API_KEY, AGENTMAIL_INBOX_ID, ANICCA_REPORT_TO]
  invariants:
    - Never block on LLM failure — fall back to header-only email
    - Never send from Dais's Gmail — send only from anicca-genesis@agentmail.to
    - LLM cost per fire ≤ $0.01 (enforced via prompt size cap of 2000 chars)
---

# daily-report

## What it does
Composes and sends ONE USEFUL email per day at 06:00 JST that proves Anicca is alive and
maps to LAUNCH MATRIX row ⑤d (`docs ✓ daily email arrives`). The email is sent FROM
Anicca's sovereign inbox (`anicca-genesis@agentmail.to`) so the identity is Anicca's,
not Dais's.

## Data sources (read-only)
| path | what |
|---|---|
| `~/.openclaw/skills/cfo-core/data/anicca-cfo.json` | MRR / revenue / runtime cost / net / wallet / status |
| `~/.hermes/state/heartbeat.jsonl` | last-24h heartbeat ok ratio |
| `~/.openclaw/skills/anicca-friction-fixer/state/violations.jsonl` | friction-fixer errors (pattern_id / fix_script / exit_code / evidence) |
| `~/.openclaw/state/friction-sweep.log` | constitution-violations text grep |

## Output
- ONE email per day via AgentMail Python SDK.
- ONE JSONL trace line appended to `~/.hermes/state/daily-report.jsonl`.

## Invocation
`hermes cron` triggers `scripts/daily-report.sh` (via the `~/.hermes/scripts/daily-report.sh`
wrapper, required by the v0.12.0 traversal guard) at `0 6 * * *`. The script composes,
sends, and exits 0 regardless of inner failures (per spec, the cron must not retry-loop
on transient errors — the next 24-hour window does).

## Failure mode
- LLM unreachable → header-only email (no bullets), `compose.llm_tokens=0`.
- AgentMail API down → trace line `send.ok=false`, NO email, NO exception propagated, **AND one `severity=critical` row appended to `~/.hermes/state/daily-report-alerts.jsonl`** so the closure gate (≥ 7 consecutive `send.ok=true` AND zero critical alerts in the same window) detects the outage. Exit code stays 0 so the cron job survives.
- CFO data stale (>26 h) → still sends, with status field reflecting the stale read.

## Transition: two emails per day
Until LAUNCH-GATE #341 retires the legacy OpenClaw `anicca-report` skill, Dais receives TWO daily emails — the legacy one at 18:00 JST and this one at 06:00 JST. The Hermes-native send carries SMTP header `X-Anicca-Origin: hermes-genesis`; cross-checking that header is the canonical way to attribute which send proves #330.

## Wave 2 (not yet built)
- Weekly Monday 09:00 digest via `--weekly` flag, separate cron entry.
- HTML email styling.
- Token-accurate cost via `hermes insights` once that API stabilizes.
