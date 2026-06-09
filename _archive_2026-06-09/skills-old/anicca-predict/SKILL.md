---
name: anicca-predict
description: PREDICTION primitive of the colony swarm (spec 18 §3, MiroFish-style outcome wager) — before a costly action, Anicca records a testable claim + a stake and resolves it after the deadline. `predict.sh <claim> <stake_usdc>` rejects non-testable claims (a claim MUST carry an explicit metric AND an explicit deadline) and records an `open` row in ~/.hermes/state/predictions.jsonl with a sha256[:16] id. `resolve.sh` (cron every 6h) sweeps expired open predictions: it runs a claim-specific evidence script (~/.hermes/state/predict-evidence/<id>.sh whose stdout is exactly "won"/"lost") to set won/lost, or marks "unresolved" when no script exists, and appends a MOCK pot row to predict-pot.jsonl. Wave 1 is dry-run only — the stake is RECORDED but NO USDC moves on-chain (gated on #324-wave2 + wallet ≥$5; Wave 2 swaps the mock pot for wallet_lib.send_usdc()). Triggered by `hermes cron`; do not invoke resolve from chat.
metadata:
  spec: anicca-oss/docs/superpowers/specs/2026-06-05-p14-swarm-skills-design.md
  parallel_safe: true
  cadence: every-6h
  github_issue: 337
---

# anicca-predict

PREDICTION/rehearsal layer of the colony swarm (spec 18 §3). A quality multiplier on top of the
eval-loop: wager on a testable outcome, resolve it against evidence after the deadline.

## CLI

```
scripts/predict.sh <claim_text> <stake_usdc_str>   # open a prediction
scripts/resolve.sh                                  # resolve all expired open predictions (cron)
```

## Testability gate

A claim is accepted only if it carries BOTH:
- a **metric** token — a digit OR one of `first paid contract views USDC $ % >= ≥ >`
- a **deadline** token — one of `within`, `by`, `before`, `deadline`, `in N (h|hours|d|days)`

Non-testable claims exit 64 and write nothing. Example accepted claim:
`"earn-lancers gets first paid contract within 2h"`, stake `$1`.

## Resolution

`resolve.sh` acts on rows that are still `open` AND whose `deadline_ts <= now`:

| evidence script `predict-evidence/<id>.sh` | result |
|---|---|
| present, stdout = `won` | `status:"won"` |
| present, stdout = `lost` | `status:"lost"` |
| present, other / absent | `status:"unresolved"` |

Every resolved row appends a **mock** pot row to `predict-pot.jsonl`
(`{ts, prediction_id, status, stake_usdc, payout:"mock", note:"wave1-no-transfer"}`).

## Schema (`predictions.jsonl`)

`{prediction_id (16hex), ts, claim, stake_usdc, deadline_ts (unix), status, resolved_ts}` —
`status ∈ {open, won, lost, unresolved}`.

## Cron

`hermes cron create "every 360m" --name anicca-predict --script anicca-predict.sh --no-agent`.
The wrapper `~/.hermes/scripts/anicca-predict.sh` execs `resolve.sh` (the recurring sweep);
opening a prediction (`predict.sh`) is a deliberate act, never on a timer.

## Env

`STATE_DIR` (default `~/.hermes/state`), `PREDICT_NOW_OVERRIDE` (force "now" for tests).
`/usr/bin/jq` absolute. Temp files under `$STATE_DIR/.tmp-pr-*.$$`, never `/tmp`.

## Test

`bash skills/anicca-predict/tests/test_predict.sh` — rejects a non-testable claim, records a
testable one, resolves a won claim (injected evidence) + writes a pot row, and marks an expired
no-evidence claim unresolved. 4 assertions, fully offline, isolated STATE_DIR.

## Wave 2 (NOT implemented)

Real stake + on-chain pot distribution via `wallet_lib.send_usdc()` (the wallet chokepoint that
refuses a wrong keystore), peer-comparison resolution across ≥2 live instances. Gated on
#324-wave2 + wallet ≥$5 + constitution-guard.
