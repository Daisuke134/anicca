# PROP-RL-LIVE2 — Real-Ledger, Real-Repo End-to-End Gate Proof

**Executed from**: `/Users/operator/anicca/skills/earn/self-improve` (main checkout)
**Interpreter**: `env -u ANICCA_HOME /Users/operator/.local/bin/python3`
**Real repo**: `/Users/operator/anicca` (accessed read-only via `git rev-parse --show-toplevel` and
`git log -1 --grep` inside `lib/promotion_history.py::last_promotion_ts` — grep-confirmed, this is
the ONLY subprocess git usage anywhere in `promotion_history.py`/`promote_gate.py`; no
add/commit/push/checkout ever occurs in the exercised code paths). No disposable clone was made —
a full clone of the monorepo was judged unnecessary overhead given the exercised git calls are
non-mutating; this was verified by grep (`grep -n "subprocess\." lib/promotion_history.py
lib/promote_gate.py lib/promote_gate_run.py`) before running, not assumed.
**Real ledger** (`/Users/operator/anicca/skills/earn/state/earn-ledger.jsonl`): read-only throughout.
**Real repo write-safety verified**: `git rev-parse HEAD` and `git status --short` captured
before and after the run — byte-identical. `earn-ledger.jsonl` MD5 unchanged.

Raw transcript: `PROP-RL-LIVE2-raw.txt` (same directory). Script source (test-only, ran from
`/private/tmp/.../scratchpad/prop_rl_live2.py`, not committed to the repo): reproducible from this
report's step descriptions below.

## What was executed (7 steps, all against REAL production code — no mocking of gate logic)

1. **Built a genuinely eligible candidate** using the real `tests/conftest.py::patched_baseline_code`
   + `write_candidate_with_fixtures` helpers (identical construction to
   `tests/test_adversary_disapprove.py::_good_candidate`) — an `edge_weight`/`conf_weight` tweak
   against the real committed baseline strategy.
2. **Real `promote_gate.assess_candidate(candidate_path)`** — the real fixture-based backtest
   (unchanged code path per REQ-RL14/15). Result: `eligible_for_adversary_review: True` (scope_guard
   OK, stage1 PASS, stage2 PASS, tripwire clear).
3. **Real `promote_gate.compute_realized_gate(mean_backtest_net_usd=assessment["mean_oos_net_usd"],
   repo_cwd=repo_root)`** against the real ledger + real repo git history (`repo_root` resolved via
   the real `promote_gate_run._repo_root()` → `/Users/operator/anicca`).
4. **Independent hand re-derivation** of the same `realized_gate` dict: called
   `promotion_history.last_promotion_ts` directly, then `ledger_reader.confirmed_net_series` +
   `gate_math.realized_window_split`/`is_worsening_trend`/`realized_trend_blocks`/`data_realism_gap`
   directly, and compared every field against step 3's output.
5. **Real `decide_promotion(assessment, adversary_verdict=None, realized_gate=realized_gate)`**
   — the exact call shape `promote_gate_run.main()` uses at its adversary-unavailable call site.
6. **Real, end-to-end `promote_gate_run.main()`** invoked with the real candidate, real ledger, real
   repo, `--dry-run` (promote_gate_run.py's own documented "--dry-run = zero file/git side effects"
   contract), and `_resolve_claude_bin` monkeypatched to a nonexistent path (`/tmp/definitely-does-
   not-exist-claude-binary-xyz`) — **not** the real `claude` CLI, to avoid real LLM spend as the
   delegating instructions permit. This exercises the actual `FileNotFoundError` → fail-closed branch
   inside `_invoke_adversary`/`main()`.
7. **`resolved=False` unconditional-block proof**: `ledger_reader.resolve_ledger_path` was
   monkeypatched (ONE function, disclosed) to return `("", False, "unresolved_no_file_context")` —
   the exact tuple the code itself defines (`ledger_reader.py` lines 63-66) for the only real
   trigger of `resolved=False` ("this process cannot determine its own module `__file__` at all").
   The REAL `compute_realized_gate` was then called (its own branching logic at lines 196-211 built
   the resulting dict — nothing hand-typed), and the REAL `decide_promotion` was called with the
   REAL, already-proven-eligible assessment from step 2 and `adversary_verdict="PASS"` (the most
   favorable possible value, chosen specifically to prove the resolved=False block overrides even a
   hypothetically-approving adversary).

## Results (actual observed values)

| step | result |
|---|---|
| 2. `assess_candidate` | `eligible_for_adversary_review: True` |
| 3. `compute_realized_gate` (real) | `resolved: true, resolution_source: "file_relative_default", row_count: 0, sufficient: false, window_net_usd: 0.0, worsening: false, trend_blocks: false, realism_gap_blocks: false, window_start_ts: 1783485137.0` |
| 4. hand-derivation vs. step 3 | **exact match on every field** (`HAND-COMPUTATION MATCHES REAL compute_realized_gate() OUTPUT: True`) |
| 5. `decide_promotion` (adversary_verdict=None) | `promote: false, reason: "fresh adversary verdict was 'MISSING', not PASS", adversary_verdict: "MISSING"` |
| 6. real end-to-end `main()` (`--dry-run`, adversary unreachable) | return code 0; `verdict.json`: `promote: false, adversary_invoked: true, reason: "adversary unavailable/erroring: claude binary not found ..."` |
| 6b. real `realized_gate.json` written by the run | identical shape/values to step 3 (`row_count: 0`, `window_start_ts: 1783485137.0`) |
| 7. forced `resolved=False` + `adversary_verdict="PASS"` | `promote: false, reason: "realized ledger identity unresolved (resolution_source='unresolved_no_file_context'): promotion blocked pending instance identity resolution"` |
| repo write-safety | `git rev-parse HEAD` before/after: identical. `git status --short` before/after: identical (both empty of new changes). `earn-ledger.jsonl` MD5 unchanged. |

Note on `row_count: 0`: the real repo's most recent promotion commit touching
`strategies/pm_backtest_strategy.py` is recent enough (`window_start_ts=1783485137`, i.e.
2026-07-08) that zero of the real ledger's 6 profitable/confirmed rows fall inside
`[window_start_ts, window_end_ts)` at the time this proof ran — this is expected, real production
behavior (not a test artifact), and step 4's independent hand-derivation reproduces the exact same
`row_count: 0` from the same real data, confirming the windowing logic itself is correct even in
this specific real, low-row-count-post-promotion state.

## Verdict

**PROVED.** The real gate wiring (`assess_candidate` → `compute_realized_gate` →
`decide_promotion` → `promote_gate_run.main()`) produces the hand-predicted outcome end-to-end
against real ledger data and real repo git history (REQ-RL7-13, RL17). The `resolved=False`
unconditional block (REQ-RL7) fires even for a genuinely eligible candidate with the most favorable
possible adversary verdict. The adversary-unavailable fail-closed branch (EDGE-3) fires correctly
through the real `main()` without any real LLM spend. Zero writes to the real repo or real ledger
occurred (verified via HEAD/status diff and ledger MD5, not merely asserted).
