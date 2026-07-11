# self-heal-allslots — Verification Architecture (lean)

## Purity Boundary Map
- **Pure Core**: `skills/self/earning-health.py::is_fresh_but_barren` (existing, untouched, already
  proof-obligated by `skills/self/tests/test_earning_health.py`).
- **New pure-ish transform**: registry JSON -> per-slot rows (embedded as a `python3 -c` one-shot
  inside the shell script; exercised indirectly via the shell wiring tests below — a dedicated pure
  unit test isn't split out separately because the transform has no branching logic of its own
  beyond field extraction with defaults, which the wiring tests already cover end-to-end).
- **Effectful Shell**: `skills/self/earning-health-allslots.sh` (file reads, `self-fix.sh` spawn via
  `SELF_FIX_DRYRUN=1` test seam, marker/log writes).

## Proof Obligations
| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-AS-001 | Registry with N slots (barren/healthy/no-trace/not-instrumented mix) produces the correct per-slot verdict for each, in one run | 1 | true | bash wiring test (mirrors `test_sol_trade_healthcheck.sh`) |
| PROP-AS-002 | BARREN slot invokes `self-fix.sh` with exactly that slot's `selfFixTarget`, never another slot's | 1 | true | bash wiring test, `SELF_FIX_DRYRUN=1` seam |
| PROP-AS-003 | Same-slot BARREN within `escalateEveryHrs` does not re-invoke `self-fix.sh` (per-slot marker, not a single shared marker) | 1 | true | bash wiring test |
| PROP-AS-004 | `instrumented:false` entries NEVER produce a `self-fix.sh` call and NEVER log OK/BARREN (only NOT-INSTRUMENTED) | 1 | true | bash wiring test |
| PROP-AS-005 | Missing registry file / missing trace file never crashes (exit 0, clean log line) | 1 | true | bash wiring test |
| PROP-AS-006 (regression) | `earning-health.py`'s own 9 pure-predicate tests still pass unmodified | 0 | true | `python3 skills/self/tests/test_earning_health.py` |

## Verification Strategy
- Tier 0: `is_fresh_but_barren` itself — no new proof needed, it is reused verbatim and already has
  Tier-1-equivalent example-based coverage from its own prior sprint.
- Tier 1: every new behavior (registry iteration, per-slot marker isolation, not-instrumented
  documentation, self-fix scoping) is covered by example-based bash wiring tests using the same
  `SELF_FIX_DRYRUN=1` seam `self-fix.sh` already exposes — no real tmux/claude spawn, no real
  `~/.openclaw` state touched (isolated tmpdir per test run).
- Tier 2/3: not applicable — this is shell/JSON orchestration around an already-verified pure
  predicate, not new algorithmic logic warranting property-based fuzzing or formal proof.
