# forum-rollout (#338) — operator notes

Closes the forum loop: **CONSENSUS (text) → real action**. Sibling of `forum-issues`
(decides) and `self-manage` (the deliberate self-edit executor it dispatches to).

## One-screen mental model

```
forum-issues  ──► CONSENSUS reached on an issue
forum-rollout ──► reads `CONSENSUS:` + ```rollout fence in any thread comment
                  ──► guard ──► HARD-NO denylist ──► idempotency
                  ──► dispatch to self-manage/*.sh or gh
                  ──► log row in forum-rollout.jsonl
                  ──► (confirm only) comment ✅ evidence + close issue
```

## Modes

| invocation | effect |
|---|---|
| `rollout.sh` / `rollout.sh --dry-run` | safe: guard + denylist + idempotency; prints intended dispatch; self-manage handlers run with `DRY_RUN=1`; `gh` actions print only; jsonl `applied:false`. |
| `rollout.sh --confirm` | live: handlers/`gh` execute; comment + close on exit 0; jsonl `applied:true`. |
| `run.sh` (cron) | `--confirm` iff `~/.hermes/state/rollout-allow.flag` exists, else `--dry-run`. |

## Wave-1 default is SAFE

The cron is dry-run until Dais runs `touch ~/.hermes/state/rollout-allow.flag`. This is the
single switch that turns the swarm's self-execution on. Remove the flag to pause it.

## HARD-NO denylist (canonical chokepoints — only Dais edits)

`anicca-constitution-guard · eval-loop · anicca-payout-ubi · anicca-wallet · forum-rollout`

Any rollout block whose TARGET names one of these is logged `BLOCKED:hard-no-list` and never
dispatched — defence-in-depth on top of the constitution-guard.

## State / log

`~/.hermes/state/forum-rollout.jsonl`. Idempotency key = `(issue_n, consensus_sha)`.

## Cron

`hermes cron add --script forum-rollout.sh --schedule "every 180m" --no-agent`
(fires after the `forum-issues` 180m round; overlap is safe via idempotency).

## Tests

```bash
bash tests/test_lib.sh           # 23 unit assertions
bash tests/test_rollout_e2e.sh   # offline E2E: fixture thread → dispatch + idempotency + HARD-NO
```
