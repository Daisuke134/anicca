# self-heal-allslots — Verification Architecture (lean)

## Purity Boundary Map
- **Pure Core**: `skills/self/earning-health.py::is_fresh_but_barren` + `sanitize_for_prompt`
  (`is_fresh_but_barren` extended, `sanitize_for_prompt` newly added, both THIS feature's own
  iteration-1 fixes — FIND-001 error-state extension, FIND-005 prompt-injection neutralization —
  proof-obligated by `skills/self/tests/test_earning_health.py`, 18 `chk(...)` checks, up from 9).
- **New pure-ish transform**: registry JSON -> per-slot rows (embedded as a `python3 -c` one-shot
  inside the shell script; exercised indirectly via the shell wiring tests below — a dedicated pure
  unit test isn't split out separately because the transform has no branching logic of its own
  beyond field extraction with defaults, which the wiring tests already cover end-to-end).
- **Effectful Shell**: `skills/self/earning-health-allslots.sh` (file reads, `self-fix.sh` spawn via
  the `EARNHC_SELF_FIX_SCRIPT` stub-capture seam for BLOCKER-text-level proofs, or
  `SELF_FIX_DRYRUN=1` for anti-spam/no-repeat-invocation-only proofs, marker/log writes).

## Proof Obligations
| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-AS-001 | Registry with N slots (barren/healthy/no-trace/not-instrumented mix) produces the correct per-slot verdict for each, in one run | 1 | true | bash wiring test (mirrors `test_sol_trade_healthcheck.sh`) |
| PROP-AS-002 | BARREN slot invokes `self-fix.sh` with exactly that slot's `selfFixTarget`, never another slot's | 1 | true | bash wiring test, `EARNHC_SELF_FIX_SCRIPT` stub-capture seam |
| PROP-AS-003 | Same-slot BARREN within `escalateEveryHrs` does not re-invoke `self-fix.sh` (per-slot marker, not a single shared marker) | 1 | true | bash wiring test, `SELF_FIX_DRYRUN=1` seam |
| PROP-AS-004 | `instrumented:false` entries NEVER produce a `self-fix.sh` call and NEVER log OK/BARREN (only NOT-INSTRUMENTED) | 1 | true | bash wiring test |
| PROP-AS-005 | Missing registry file / missing trace file never crashes (exit 0, clean log line) | 1 | true | bash wiring test |
| PROP-AS-006 (regression) | `earning-health.py`'s own pure-predicate test suite (`is_fresh_but_barren` incl. FIND-001 error-state extension) still passes — 18 `chk(...)` checks, up from the pre-feature 9 | 0 | true | `python3 skills/self/tests/test_earning_health.py` |
| PROP-AS-007 | `sanitize_for_prompt` strips every shell/prompt-injection metacharacter from a malicious trace-derived reason, preserves safe substrings, hard-caps length, and is fail-soft on non-string input (FIND-005); the shell caller's empty-after-sanitize fallback (`REASON`/`SAFE_ID` -> `"unspecified"`/`"unspecified-slot"`) produces a valid, non-empty structured self-fix message (FIND-003, iter2) | 1 | true | `python3 skills/self/tests/test_earning_health.py` (pure unit) + `test_earning_health_allslots.sh` (D)/(E) blocks, `EARNHC_SELF_FIX_SCRIPT` stub-capture seam (end-to-end BLOCKER-text proof) |

## Verification Strategy
- Tier 0: `is_fresh_but_barren` itself — no new proof needed beyond PROP-AS-006's regression run; its
  core control flow is reused verbatim and already has Tier-1-equivalent example-based coverage from
  its own prior sprint (the FIND-001 error-state extension is covered by PROP-AS-006's own suite).
- Tier 1: every new behavior (registry iteration, per-slot marker isolation, not-instrumented
  documentation, self-fix scoping, FIND-005 prompt-sanitization) is covered by example-based bash
  wiring tests. Anti-spam/no-repeat-invocation proofs (PROP-AS-003) use the `SELF_FIX_DRYRUN=1` seam
  `self-fix.sh` already exposes; the dual-barren cross-fire proof (PROP-AS-002) and the
  sanitization-neutralization proof (PROP-AS-007/FIND-005) additionally depend on
  `EARNHC_SELF_FIX_SCRIPT`, a newly-added stub-script capture seam — `SELF_FIX_DRYRUN=1` alone
  cannot prove either because it never echoes the BLOCKER text itself (see
  `test_earning_health_allslots.sh`'s own comment above its (A)/(D) blocks). No real tmux/claude
  spawn, no real `~/.openclaw` state touched (isolated tmpdir per test run).
- Tier 2/3: not applicable — this is shell/JSON orchestration around an already-verified pure
  predicate, not new algorithmic logic warranting property-based fuzzing or formal proof.
