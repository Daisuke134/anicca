# Purity Boundary Audit — self-improve-real-ledger (VCSDD Phase 5)

Compares the implemented core/shell split against the boundary declared in
`specs/verification-architecture.md`'s "Purity Boundary Map" (Phase 1b).

## Declared Boundaries

**Pure Core** (declared, extends `lib/gate_math.py`, no new pure module — INV-RL6):
`realized_window_split`, `is_worsening_trend`, `realized_trend_blocks`, `data_realism_gap` (all in
`lib/gate_math.py`); plus `is_confirmed`/`is_profitable` in `lib/ledger_reader.py` (declared as
"mislabeled — pure functions living in an otherwise-impure module").

**Effectful Shell** (declared): `lib/ledger_reader.py::resolve_ledger_path` (env + `__file__`
read, no ledger file access) / `read_ledger`+`realized_summary` (real file read) /
`lib/promotion_history.py::last_promotion_ts` (new file, `subprocess` git) /
`lib/promote_gate.py::compute_realized_gate` (new function, orchestrates I/O then calls pure
`gate_math`) / `lib/promote_gate.py::decide_promotion` (extended, still pure — `realized_gate` is
an already-computed dict passed in) / `promote_gate_run.py::main` (extended) /
`evaluator.py::evaluate`/`evaluate_stage2` (extended, reads ledger additionally to fixture) /
`lib/scope_guard.py::DENYLIST_MODULES` (extended constant, no I/O) / `run_evolve.sh` (unchanged
shell).

## Observed Boundaries

Verified by re-running the SAME AST/text import-scan the prior phase (`anicca-self-improve-harness`)
wrote for `gate_math.py`'s purity (per verification-architecture.md's own stated method — "re-run,
not re-written"), plus a manual read of every file this feature touched:

| item | declared | observed | match |
|---|---|---|---|
| `gate_math.py` (4 new functions) | pure, no `os`/`subprocess`/`pathlib`/`requests`/`urllib`/`socket` | confirmed — `git diff main~5..main -- skills/earn/self-improve/lib/gate_math.py` shows only new top-level `def` bodies operating on already-injected args (`rows`, `window_start_ts`, `window_end_ts`, floats, bools); no new imports added to the file | ✅ |
| `is_confirmed`/`is_profitable` (`ledger_reader.py`) | pure predicates over an injected dict | confirmed — both take `line: dict` and return `bool`/derive from `line.get(...)`, zero I/O calls in either body | ✅ |
| `resolve_ledger_path` | impure (env + `__file__`), but itself never opens the ledger file | confirmed — reads `os.environ.get("ANICCA_HOME")` and `os.path.abspath(__file__)` only; the actual `open(ledger_path)` happens in the separate `read_ledger` function, never inside `resolve_ledger_path` | ✅ |
| `compute_realized_gate` (`promote_gate.py`, new) | impure orchestrator: does the ledger read + `last_promotion_ts` call, THEN calls the pure `gate_math` functions with plain data | confirmed by read — function body is: (1) call `ledger_reader.resolve_ledger_path`/read confirmed rows → plain `(ts, net)` tuples, (2) call `promotion_history.last_promotion_ts` → float/None, (3) call `gate_math.realized_window_split`/`is_worsening_trend`/`realized_trend_blocks`/`data_realism_gap` with those already-resolved plain values. It never re-implements the pure functions' branching logic inline (would be a purity-boundary violation: gating math duplicated outside the pure layer) | ✅ |
| `decide_promotion` (extended) | still pure — `realized_gate` is a caller-supplied already-computed dict | confirmed — the new `realized_gate` parameter is read via `.get(...)` only, no I/O, no call into `compute_realized_gate` or any impure function from inside `decide_promotion` itself | ✅ |
| `evaluator.py::evaluate`/`evaluate_stage2` | reads the real ledger ADDITIONALLY to the fixture; `combined_score` computation path UNCHANGED (still 100% fixture-derived) | confirmed by PROP-RL-EVAL1's own proof (this session's fresh 101-test run includes it): `combined_score`'s numeric value is asserted IDENTICAL whether `data_source` is `"fixture"` or `"fixture+realized-crosscheck"` — the ledger read only changes an informational tag, never the score math | ✅ |
| `promote_gate_run.py::main` | impure: calls `compute_realized_gate`, writes `realized_gate_escalation.json` when blocked, passes `realized_gate=` to every `decide_promotion` call site | confirmed by PROP-RL-WIRE1 (AST-walk assertion, part of the 101-test suite) — every `decide_promotion(` call site in the file has a `realized_gate=` keyword; and by PROP-RL-LIVE2's real end-to-end run, which observed the real `verdict.json`/`realized_gate.json` writes | ✅ |
| `scope_guard.py::DENYLIST_MODULES` | extended constant, no I/O, superset of the pre-existing tuple | confirmed by PROP-RL-SAFE1 (set-difference assertion against a committed pre-feature snapshot, part of the 101-test suite) | ✅ |
| No pure function performs file/env/subprocess I/O | — | confirmed by the same import-scan technique the prior phase established (grep for `import os`/`subprocess`/`requests`/etc. inside `gate_math.py` — zero matches beyond the pre-existing module-level imports, none of which are used inside the 4 new functions) | ✅ |

## Money-safety boundary (REQ-RL20/RL21, PROP-RL-SAFE2/SAFE3 — not part of the declared
Purity Boundary Map itself, but load-bearing for this audit given this feature reads a real
financial ledger)

- **No write path to `earn-ledger.jsonl`**: static source-text scan (PROP-RL-SAFE2, part of the
  101-test suite) finds zero `open(..., "w"/"a")` calls whose path argument contains
  `"earn-ledger"` anywhere in this feature's touched files. Independently reconfirmed by
  PROP-RL-LIVE1/LIVE2's own write-safety checks (file read-only throughout, HEAD/status/MD5
  diffed before and after).
- **No private-key/wallet-file references**: static source-text scan (PROP-RL-SAFE3) finds zero
  references to `ANICCA_EVM_PRIVATE_KEY`/`ANICCA_SOLANA_PRIVATE_KEY`/`.automaton/wallet.json`/
  `.automaton/solana.json`/`.blockrun/.solana-session` in any file this feature touches. This
  feature only ever reads `earn-ledger.jsonl` (an append-only, already-recorded outcome log, not a
  credential or a live trading surface) and git history (read-only).

## Summary

The implemented core/shell split matches the declared Purity Boundary Map with **zero
deviations**: every function classified as "pure" in Phase 1b remains provably free of I/O (import
scan, byte-identical technique to the prior phase), and every impure function's role is exactly
"snapshot real state into plain data, then hand it to the pure layer" — none of the effectful
shell functions re-implement gating math inline, and none of the pure functions perform I/O. The
money-safety boundary (this feature's central risk, since it reads a real financial ledger) is
independently double-covered: by static source-scan (SAFE2/SAFE3) AND by the live-tier proofs'
own before/after write-safety diffs (LIVE1/LIVE2). No purity or money-safety violation found.
