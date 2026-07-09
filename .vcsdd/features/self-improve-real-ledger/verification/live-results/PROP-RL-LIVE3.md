# PROP-RL-LIVE3 — Real `run_evolve.sh` Execution, OBSERVE Step Proof

**Executed from**: `/Users/anicca/anicca/skills/earn/self-improve` (main checkout)
**Command actually run**:
```
env -u ANICCA_HOME SELF_IMPROVE_ITERATIONS=1 timeout 240 bash run_evolve.sh
```
`SELF_IMPROVE_ITERATIONS=1` used the script's own documented override (`ITERATIONS="${SELF_IMPROVE_ITERATIONS:-20}"`,
`run_evolve.sh` line ~46) to keep this a small, fast real run — not a mock/stub, a genuine
1-iteration `openevolve-run` invocation against the real venv (`~/.anicca-venvs/self-improve/bin/`)
and the real local ClawRouter free-tier model proxy (`http://127.0.0.1:8402/v1`, confirmed reachable
via `curl` before running). `timeout 240` was a safety bound only — **the run completed naturally
on its own in ~17 seconds and exited 0**; the timeout was never triggered and no kill was needed.

## Termination

Natural completion, exit code 0. No manual kill/timeout intervention was required.

## Observed OBSERVE line (REQ-RL16)

Captured from `/Users/anicca/anicca/skills/earn/state/self-improve-evolve.log` (new lines appended
by this run only, full excerpt in `PROP-RL-LIVE3-log-excerpt.txt`, same directory):

```
2026-07-08T23:25:11Z OBSERVE realized_ledger={"ledger_path": "/Users/anicca/anicca/skills/earn/state/earn-ledger.jsonl", "total_rows": 30, "profitable_row_count": 6, "realized_net_usd": 8.4731, "resolved": true, "resolution_source": "file_relative_default"}
```

This is exactly the REQ-RL16 assertion: `resolved: true`, `resolution_source:
"file_relative_default"`, pointing at the real ledger path
(`/Users/anicca/anicca/skills/earn/state/earn-ledger.jsonl`) — logged BEFORE `openevolve-run` was
even invoked, with `ANICCA_HOME` unset (the OSS checkout's own production condition).

## What happened after OBSERVE (informational, not required for REQ-RL16 but shows full real behavior)

The real `openevolve-run` (1 iteration, `free/gpt-oss-120b` via the local proxy) genuinely ran and
found a best candidate (`combined_score=2.7798`), which `promote_gate.sh`/`lib/promote_gate.py`
assessed for real: `stage1_pass=True` but `stage2_pass=False` (did not beat baseline,
`combined_score=2.7798 < baseline_stage2_score=3.2076`) → `eligible_for_adversary_review=False` →
**no adversary LLM call was made, zero cost, zero writes to the committed baseline strategy file.**

## Write-safety verification

| check | result |
|---|---|
| `strategies/pm_backtest_strategy.py` MD5 before vs. after | identical (`7173b8bc6d969fff3e4582d450a31706`) |
| `git status --short skills/earn/self-improve/` | empty (no tracked-file changes) |
| New files produced | `runs/run-20260708T232511Z/**` (gitignored via `skills/earn/self-improve/.gitignore`'s `runs/` entry) and appended lines in `skills/earn/state/self-improve-evolve.log` (gitignored via that same file's `state/` entry) — both are the script's own designed, gitignored output locations, not repo writes |

## Verdict

**PROVED.** One real, human-zero execution of `run_evolve.sh` (`ANICCA_HOME` unset) produced the
exact `resolved: true` / `resolution_source: "file_relative_default"` OBSERVE line pointing at the
real per-instance ledger path, satisfying REQ-RL16. The run completed naturally; no kill switch was
needed. No writes occurred to any tracked repo file.

Raw stdout: `PROP-RL-LIVE3-stdout.txt`. Full new log excerpt: `PROP-RL-LIVE3-log-excerpt.txt` (both
same directory).
