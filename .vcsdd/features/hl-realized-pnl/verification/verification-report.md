# Verification Report — hl-realized-pnl (Phase 5: Formal Hardening)

Feature: `hl-realized-pnl` (strict mode, language=python). Worktree
`/Users/operator/anicca/.worktrees/hl-realized-pnl`, branch `feature/hl-realized-pnl`, HEAD
`486bef6`, clean tree before and after this hardening pass — no production code was modified.

Environment used: a disposable scratch venv
(`.../scratchpad/hl-verify/.venv`, Python 3.14.6) with `pytest 9.1.1`, `hypothesis 6.156.3`,
`hyperliquid-python-sdk`, `eth_account`, and `bandit 1.9.4` installed — separate from the
worktree/repo, so no dependency was added to the feature's own tree. `semgrep 1.168.0` (Homebrew
install, pre-existing on this machine) was run directly against the worktree files.

## Proof Obligations

| ID | Tier | Req'd | Verification method | Result | Evidence |
|---|---|---|---|---|---|
| PROP-001 | 0 | yes | `pytest tests/test_fills.py` (3 fixture cases) + NEW `test_prop001_net_usdc_always_equals_closed_pnl_minus_fee` (Hypothesis, 500 random `(closed_pnl, fee)` pairs) | **PROVED** | fixture tests all PASS (full pytest run below); hypothesis 500/500 passing, 0 failing — `verification/fuzz-results/hypothesis-run.log` |
| PROP-002 | 0 | yes | `pytest tests/test_fills.py::test_select_close_fills_excludes_zero_pnl_and_time_strictly_before_since` + NEW `test_prop002_select_close_fills_output_is_exactly_time_ge_since_and_nonzero_pnl` (Hypothesis, 300 random fill-list/since_time_ms combos) | **PROVED** | fixture PASS; hypothesis 300/300 passing, 31 filtered-invalid (Hypothesis's own precondition rejection, not failures), 0 failing |
| PROP-002b | 0 | yes | `pytest tests/test_fills.py::test_select_close_fills_boundary_is_inclusive_not_exclusive` + NEW `test_prop002b_boundary_is_inclusive_for_any_tied_timestamp` (Hypothesis, 200 random tied-timestamp cases) | **PROVED** | fixture PASS; hypothesis 200/200 passing, 0 failing |
| PROP-003 | 0 | yes | `pytest tests/test_fills.py` (5 `is_unprocessable` cases) | **PROVED** | all 5 PASS |
| PROP-004 | 0 | yes | `pytest tests/test_reconcile.py::test_reconcile_never_calls_record_line_fn_for_an_already_recorded_tid` + `test_plan_batch_marks_already_recorded_tid_as_skip_duplicate_and_never_stops` + NEW `test_prop004_005_plan_batch_stop_index_and_no_gap_invariants` (Hypothesis, 300 random candidate-lists × already-recorded sets) | **PROVED** | fixture tests PASS; hypothesis 300/300 passing, 20 filtered-invalid, 0 failing |
| PROP-005 | 0 | yes | `pytest tests/test_reconcile.py::test_plan_batch_stops_at_first_unprocessable_fill_and_never_plans_past_it` + `test_reconcile_checkpoint_stops_before_unprocessable_fill_t3_never_attempted` + the same Hypothesis test as PROP-004 (shared stop-index/no-gap invariant) | **PROVED** | all PASS |
| PROP-006 | 0 | yes | `pytest tests/test_reconcile.py::test_reconcile_stops_batch_when_record_line_fn_raises_on_second_fill` | **PROVED** | PASS |
| PROP-007 | 0 | yes | `pytest tests/test_reconcile.py::test_reconcile_full_successful_batch_checkpoint_is_last_fills_time_not_first` + `test_reconcile_py_writes_checkpoint_atomically_static_grep`; independently re-verified `grep -n "os.replace" lib/reconcile.py` (1 match, line 95, the `os.replace(tmp_path, path)` call itself) and `grep -nE "open\([^)]*checkpoint[^)]*['\"]w['\"]" lib/reconcile.py` (0 matches) | **PROVED** | PASS; static greps re-run manually, same result as the unit test asserts |
| PROP-008 | 0 | yes | `pytest tests/test_reconcile.py::test_reconcile_zero_eligible_fills_leaves_checkpoint_byte_identical` | **PROVED** | PASS |
| PROP-009 | 0 | yes | `pytest tests/test_reconcile.py` (missing/corrupt/empty checkpoint, 3 tests) | **PROVED** | all 3 PASS |
| PROP-010 | 0 | yes | `pytest tests/test_reconcile.py::test_reconcile_queries_user_fills_by_time_inclusive_not_plus_one` + `test_reconcile_py_never_calls_unbounded_user_fills_static_grep`; re-verified `grep -n "since_time_ms + 1\|since_time_ms+1" lib/reconcile.py` → 0 matches | **PROVED** | PASS |
| PROP-010b | 0 | yes | `pytest tests/test_reconcile.py::test_tied_timestamp_partial_stop_recovers_the_sibling_fill_on_the_next_pass` | **PROVED** | PASS |
| PROP-011 | 0 | yes | `pytest tests/test_reconcile.py::test_reconcile_api_error_returns_status_and_leaves_checkpoint_untouched` | **PROVED** | PASS |
| PROP-012 | 0 | yes | `pytest tests/test_reconcile.py::test_reconcile_builds_payload_with_exactly_the_req_c1_keys` | **PROVED** | PASS |
| PROP-013 | 0 | yes | `node --test skills/_shared/lib/__tests__/ledger.test.mjs` (2 `deriveLine`/`fill_tid` tests) | **PROVED** | PASS (12/12 in this file, see node run below) |
| PROP-014a | 0 | yes | `ledger.test.mjs` — well-formed HL win | **PROVED** | PASS |
| PROP-014b | 0 | yes | `ledger.test.mjs` — HL loss rejected | **PROVED** | PASS |
| PROP-014c | 0 | yes | `ledger.test.mjs` — missing/false `external` rejected (2 tests) | **PROVED** | PASS |
| PROP-014d | 0 | yes | `ledger.test.mjs` — malformed HL shape rejected (2 tests) | **PROVED** | PASS |
| PROP-014e | 0 | yes | `ledger.test.mjs` non-regression fixtures (4 tests) + re-ran the PRE-EXISTING `ledger.test.js` (9/9 PASS, untouched) as an independent non-regression check | **PROVED** | PASS; pre-existing suite unaffected |
| PROP-015 | 0 | yes | `pytest tests/test_reconcile.py::test_reconcile_py_never_reimplements_ledger_guards_static_grep`; independently re-ran `grep -n "appendLedger\|assertOwnIdentityOnly\|checkHalt" lib/reconcile.py` (0 matches) and `grep -n "record.mjs" lib/reconcile.py` (2 matches) | **PROVED** | PASS; see `verification/purity-audit.md`'s independent re-derivation |
| PROP-016 | 0 | yes | `pytest tests/test_reconcile.py::test_reconcile_py_never_loads_a_second_signing_key_static_grep` + `test_hl_py_cmd_reconcile_reuses_clients_static_grep` | **PROVED** | PASS |
| PROP-017 | 0 | yes | `pytest tests/test_reconcile.py::test_reconcile_py_never_places_modifies_or_cancels_orders_static_grep` | **PROVED** | PASS |
| PROP-018 | 0 | yes | `pytest tests/test_reconcile.py::test_hl_py_has_no_closed_pnl_usd_field_static_grep` + `test_hl_py_cmd_close_json_output_has_no_closed_pnl_usd_key` — the LATTER was SKIPPED in the earlier phases (no `hyperliquid-python-sdk` in the ambient interpreter); Phase 5 installed the SDK into the scratch venv and RE-RAN — now executes and PASSES (no longer skipped) | **PROVED** | both PASS; this closes a coverage gap left open through Phase 3 |
| PROP-019 | 0 | yes | `pytest tests/test_reconcile.py::test_run_sh_calls_hl_reconcile_before_cooldown_and_close_branch_static_grep`; independently re-verified `grep -n "hl.py\" reconcile"` → line 177 vs `grep -n "_hl_since="` → line 205 (177 < 205) | **PROVED** | PASS |
| PROP-020 | 1 | no | Diff review: `grep -n "'external'" skills/earn/run.sh` shows exactly 2 matches, both PRE-EXISTING/unrelated to HL (line 146 `source:'0xwork'`, line 413 `source: yield-proto`); none of the HL branch's own JSON snippets (`hl-cooldown` line 209, `hl-observe` line 231, `hl-fund-skipped` line 247, `hl open` line 255) gained an `external` key | **PROVED** | manually re-verified, matches spec claim |
| PROP-021 | 2 | yes (Done-gating) | Live E2E — **RE-RUN fresh for Phase 5** (not reused from the Phase 3 snapshot), per verification-architecture.md's own §Done instruction ("Phase 5 hardening SHALL re-run this live"). See dedicated section below. | **PROVED** | `verification/prop-021-phase5-rerun-pass1.log`, `verification/prop-021-phase5-rerun-pass2.log`, `verification/prop-021-phase5-scratch-ledger.jsonl` |
| PROP-022 | 0 | yes | `pytest tests/test_reconcile.py::test_acquire_lock_second_caller_gets_none_while_first_holds_it` + `test_reconcile_returns_locked_status_and_touches_nothing_when_lock_held` + `test_reconcile_py_uses_real_flock_static_grep` | **PROVED** | all PASS (real `fcntl.flock`, not a fake) |
| PROP-023 | 0 | yes | `pytest tests/test_reconcile.py::test_reconcile_py_never_hardcodes_another_instances_home_or_absolute_user_path_static_grep`; independently re-verified `grep -n "\.blockrun\|\.anicca\|\.openclaw\|/Users/" lib/reconcile.py` → 0 matches | **PROVED** | PASS |
| PROP-024 | 0 | yes | `pytest tests/test_reconcile.py::test_run_sh_never_references_closed_pnl_usd_anywhere` + `test_run_sh_close_branch_never_calls_record_line_for_its_own_pnl_line` | **PROVED** | PASS |

**Totals: 30/30 obligations PROVED (28/28 required Tier-0 + 1/1 Tier-1 + 1/1 required Tier-2). 0 FAILED.**

## Full test-suite run (this Phase 5 pass, fresh execution)

```
$ <scratch-venv>/bin/python3 -m pytest skills/earn/hl-trade/tests/ -v
...
42 passed in 5.51s
```
(all 42 pre-existing pytest cases pass — the one previously-SKIPPED test
(`test_hl_py_cmd_close_json_output_has_no_closed_pnl_usd_key`, PROP-018) now executes and passes
since Phase 5 installed `hyperliquid-python-sdk` into the verification environment.)

```
$ node --test skills/_shared/lib/__tests__/ledger.test.mjs
...
tests 12 / pass 12 / fail 0

$ node --test skills/_shared/lib/__tests__/ledger.test.js   (pre-existing, non-regression check)
...
tests 9 / pass 9 / fail 0
```

```
$ <scratch-venv>/bin/python3 -m pytest verification/proof-harnesses/test_properties.py -v --hypothesis-show-statistics
...
4 passed in ~1s
  test_prop001...: 500 passing examples, 0 failing
  test_prop002...: 300 passing examples, 0 failing, 31 invalid (filtered)
  test_prop002b...: 200 passing examples, 0 failing
  test_prop004_005...: 300 passing examples, 0 failing, 20 invalid (filtered)
```
Full statistics output: `verification/fuzz-results/hypothesis-run.log`.

## PROP-021 — Phase 5 live E2E rerun (detail)

- **Pass 1** (fresh scratch checkpoint, starting from 0): `info.user_fills_by_time` against
  audited wallet `0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21` returned **146 raw fills** — the
  SAME count as the original audit (`evidence/audit-userfills-summary.md`) and the Phase 3 run,
  confirming the wallet's history has NOT grown since Phase 1b/Phase 3 (no NFR-1 pagination
  concern triggered — 146 is well under any HL API page-size limit). Of these, **71 fills had
  `closedPnl != 0`**. `reconcile()` recorded **71 lines** to a fresh scratch ledger
  (`verification/prop-021-phase5-scratch-ledger.jsonl`) — matches assertion (a) exactly (0
  drops, 0 fabricated extras).
- Assertion (b): the inline live-computed `SUM(closedPnl - fee)` over the 71 nonzero fills was
  **0.081756**; independently summing `net_usdc` across the 71 appended scratch-ledger lines
  (recomputed via a separate `python3` one-liner reading the JSONL file, NOT the reconcile
  process's own in-memory value) gives **0.081756** — exact match to `ledger.mjs`'s 6-decimal
  rounding tolerance.
- **Pass 2** (checkpoint now `1783370643509` from pass 1): re-querying from that checkpoint
  returned 1 raw fill (the same fill AT the checkpoint boundary itself, re-fetched because the
  boundary is inclusive per REQ-B8) — `plan_batch`'s tid-dedup correctly classified it as
  `skip_duplicate`, so `reconcile()` recorded **0 additional lines**. `wc -l` on the scratch
  ledger after pass 2 = 71 (unchanged from pass 1) — assertion (c) confirmed: idempotency holds
  against LIVE data, not just fixtures.
- Assertion (d): `grep -iE "dry|fake|mock|simulated"` across both pass logs and the scratch
  ledger returned **zero matches**.
- Assertion (e) / NFR-1: not triggered this run (146 == the previously audited full count, no
  truncation signal).
- No signing key was used or resolvable anywhere in this run (`Info(constants.MAINNET_API_URL,
  skip_ws=True)` only — no `Exchange` object was constructed). The real earn ledger
  (`skills/earn/state/earn-ledger.jsonl`) and the real hl-trade checkpoint
  (`skills/earn/hl-trade/.last-fill-ts`) were never opened by this run — confirmed by using
  exclusively scratch paths under `.../scratchpad/hl-e2e-phase5/` for `LEDGER_PATH`,
  `CHECKPOINT_PATH`, `LOCK_PATH`.

## Summary

- **28/28 required Tier-0 obligations: PROVED.**
- **1/1 Tier-1 obligation (PROP-020): PROVED.**
- **1/1 required Tier-2 obligation (PROP-021): PROVED**, via a genuinely FRESH live rerun (not a
  reuse of the Phase 3 evidence), closing the Phase 5 spec's own instruction to re-run rather
  than reuse the pre-fetched snapshot.
- **0 failed obligations.**
- One coverage gap that existed through Phase 3 is now closed: PROP-018's unit-test half
  (`test_hl_py_cmd_close_json_output_has_no_closed_pnl_usd_key`) was previously SKIPPED for lack
  of `hyperliquid-python-sdk` in the ambient interpreter; Phase 5's dedicated scratch venv now
  runs it, and it passes.
- Property-based (Hypothesis) tests added for all 4 PURE-layer components in
  `verification/proof-harnesses/test_properties.py`: 1300 total generated examples across
  compute_realized_pnl (net_usdc invariant), select_close_fills (filter/sort/inclusive-boundary
  invariants), and plan_batch (stop-index/no-gap/action-correctness invariants) — 0 failures.
- Security sweep: semgrep (auto + security-audit + secrets, 428 rule-invocations) = 0 findings;
  bandit = 9 Low-severity findings, all reviewed and accepted as correct-by-design (see
  `verification/security-report.md`); manual checklist (subprocess injection, path traversal,
  flock TOCTOU, JSON-parse DoS, secret exposure) = 0 exploitable findings.
- Purity audit: 0 boundary violations; 1 informational (non-blocking) finding about an
  undocumented in-process cache contribution to `already_recorded_tids`, and 1 naming-only
  (non-blocking) deviation (`fetch_fills` inlined rather than factored out) — see
  `verification/purity-audit.md`.
- **No production code was modified during this hardening pass.** All new artifacts are under
  `.vcsdd/features/hl-realized-pnl/verification/` or the session scratchpad. The worktree's git
  status is clean (HEAD `486bef6`) both before and after this session.
