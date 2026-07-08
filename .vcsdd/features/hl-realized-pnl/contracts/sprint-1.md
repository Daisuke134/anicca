---
sprintNumber: 1
feature: hl-realized-pnl
scope: Fill-based Hyperliquid realized-P&L reconcile engine (lib/fills.py + lib/reconcile.py + hl.py reconcile subcommand + run.sh wiring) and ledger.mjs's hyperliquid GATE-0 disjunct.
negotiationRound: 1
status: approved
criteria:
  - id: CRIT-001
    dimension: spec_fidelity
    description: Every Tier-0 REQ-B1/B2/B3 pure function (compute_realized_pnl win/loss/breakeven split, select_close_fills inclusive time+nonzero-pnl filter, is_unprocessable UNPROCESSABLE classification) matches behavioral-spec.md exactly, with the PROP-002b tied-timestamp inclusive-boundary regression green.
    weight: 0.2
    passThreshold: test_fills.py's 12 tests all pass (PROP-001/002/002b/003), including the tied-timestamp boundary test explicitly designed to fail against a strictly-greater-than implementation.
  - id: CRIT-002
    dimension: edge_case_coverage
    description: The reconciler never drops a fill across a STOP boundary — dedup (REQ-B4.1), unprocessable-stop (REQ-B4.2), and record-call-failure-stop (REQ-B4.3) all leave the checkpoint short of the failed fill, and the F-1 tied-timestamp two-pass recovery (EDGE-11/PROP-010b) actually recovers the sibling fill on the next pass.
    weight: 0.2
    passThreshold: test_reconcile.py's PROP-004/005/006/007/008/009/010/010b/011/022 all pass, including the two-call PROP-010b integration test asserting since_time_ms=500 on the re-query and fill_tid=[2,3] recorded on pass 2.
  - id: CRIT-003
    dimension: implementation_correctness
    description: reconcile()'s composition root wires the pure layer (fills.py, plan_batch) and the impure layer (fetch/record/checkpoint/lock) in exactly the REQ-B4-through-B6 order, and record.mjs's own payload shape (REQ-C1 keys) is byte-exact.
    weight: 0.15
    passThreshold: test_reconcile.py's PROP-012 (exact payload key set) and PROP-007 (checkpoint == last recorded fill's time, not first) both pass; PROP-015/016/017 static greps confirm no reimplemented appendLedger/assertOwnIdentityOnly/checkHalt, no second key-loading path, and no market_close/.order(/update_leverage call anywhere in reconcile.py; PROP-023 static check confirms REQ-D4 path isolation (checkpoint and ledger paths derived exclusively from the reconciler's own checkout location, with no literal reference to another instance's home directory).
  - id: CRIT-004
    dimension: structural_integrity
    description: hl.py's REQ-A1 fix (closed_pnl_usd field fully removed, not relabeled) and run.sh's REQ-E3 wiring (hl.py reconcile invoked before the anti-churn cooldown check and the close-action branch, on every STRATEGY=hl wake) are both structurally present, not merely described.
    weight: 0.15
    passThreshold: test_reconcile.py's PROP-018 (closed_pnl_usd absent from hl.py, and — where the hyperliquid-python-sdk venv is available — cmd_close's JSON output has no such key) and PROP-019 (hl.py reconcile line number < both _hl_since and the close-action branch line numbers in run.sh) both pass.
  - id: CRIT-005
    dimension: implementation_correctness
    description: ledger.mjs's new hyperliquid disjunct (REQ-C2/C3) is additive-only — no pre-existing EVM/Solana/narrate/swap classification result changes — and is covered by a NEW test file (ledger.test.mjs) rather than edits to the pre-existing ledger.test.js, per verification-architecture.md's file table.
    weight: 0.15
    passThreshold: ledger.test.mjs's 12 tests all pass (PROP-013, PROP-014a-e including the non-regression re-run of the EVM/Solana/narrate/swap fixtures), AND the pre-existing skills/_shared/lib/__tests__/ledger.test.js's 9 tests remain green unmodified.
  - id: CRIT-006
    dimension: verification_readiness
    description: PROP-021's Tier-2 live E2E money-correctness capstone runs against the real Hyperliquid Info API for the audited historical wallet (0xa3cdd4...) through the REAL reconcile code path into a scratch ledger (production ledger untouched), proving the pipeline derives the CORRECT real-world realized numbers from live settled fills — not fixtures.
    weight: 0.15
    passThreshold: The live E2E run per verification-architecture.md's Done section records every closedPnl!=0 fill exactly once (zero silent drops, zero fabricated extras, count cross-checked against the raw live response), the summed net_usdc equals the raw sum(closedPnl - fee) within 1e-6, an immediately repeated run appends zero additional lines (idempotency), and no recorded ledger line or E2E log line describes its own numbers as dry/fake/mock/simulated. Raw live response and run transcript saved under evidence/.
---

# Sprint 1 Contract — hl-realized-pnl

## CRIT-001 — spec_fidelity

`fills.py`'s three pure functions are the money-arithmetic and candidate-selection core this
whole feature stands on (REQ-B1/B2/B3). `test_fills.py` (12 tests) is the RED-phase proof these
functions don't exist yet (`ModuleNotFoundError` on `from fills import ...`), and once Phase 2b
implements them, EVERY one of these 12 must go green with no adjustment to the test file itself:

- `compute_realized_pnl` win/loss/breakeven split (PROP-001): `net_usdc` must equal
  `closed_pnl - fee` exactly in all three branches (float tolerance 1e-9).
- `select_close_fills`'s ordinary filter (PROP-002): excludes `time < since_time_ms` AND
  `closedPnl == 0`, sorted ascending.
- `select_close_fills`'s INCLUSIVE boundary regression (PROP-002b) — the money-safety capstone
  of this whole sprint: a tied-timestamp fixture `[tid=1@t100, tid=2@t100, tid=3@t150]` queried
  with `since_time_ms=100` MUST return all three tids in order. This is the literal test that
  fails against a `since_time_ms + 1` (strictly-greater-than) implementation and is the reason
  F-1's money-safety defect can never silently reappear.
- `is_unprocessable`'s UNPROCESSABLE classification (PROP-003): non-numeric/missing
  `closedPnl`/`fee`, missing/non-integer `tid` → `True`; the live HL API shape (numeric-string
  P&L/fee, real Python-int `tid`) → `False`.

## CRIT-002 — edge_case_coverage

The reconciler's entire money-safety argument rests on never silently dropping a fill across a
STOP boundary. `test_reconcile.py` encodes three DISTINCT STOP mechanisms and proves none of
them causes data loss:

- REQ-B4.1 (dedup): `test_reconcile_never_calls_record_line_fn_for_an_already_recorded_tid` —
  the fake `record_line_fn` raises `AssertionError` if EVER invoked for a duplicate tid; a green
  pass here proves dedup happens before any record attempt, not after.
- REQ-B4.2 (unprocessable-stop, known at plan time): `test_plan_batch_stops_at_first_unprocessable_fill_and_never_plans_past_it`
  plus the reconcile-level `test_reconcile_checkpoint_stops_before_unprocessable_fill_t3_never_attempted`
  — checkpoint lands on `t1`'s time, `t3` is never even attempted.
- REQ-B4.3 (record-call-failure-stop, only knowable at runtime): `test_reconcile_stops_batch_when_record_line_fn_raises_on_second_fill`
  — this is why PROP-006 MUST be an integration test against `reconcile()` itself and cannot be
  a `plan_batch` pure test; `plan_batch` cannot predict a runtime record failure.
- EDGE-11 / PROP-010b (the two-pass recovery capstone):
  `test_tied_timestamp_partial_stop_recovers_the_sibling_fill_on_the_next_pass` runs `reconcile()`
  TWICE against the SAME fake `info`/ledger/checkpoint state. Pass 1 must STOP at `tid=2` (Y),
  checkpoint lands on `500`. Pass 2 must re-query with `since_time_ms=500` (inclusive, not
  `501`), skip `tid=1` (X) as an already-recorded duplicate, and record `tid=2` (Y) exactly once
  — proving Y's realized P&L is never permanently lost.
- REQ-B7/B8/B9/B10 non-loss guarantees: corrupt/missing checkpoint → `0` (never crash), a fetch
  exception → `{"status":"api-error","recorded":0}` with the checkpoint byte-identical, and a
  held lock → `{"status":"locked","recorded":0}` with ZERO fetch calls (not even an attempt).

## CRIT-003 — implementation_correctness

`reconcile()`'s composition root must produce the EXACT `REQ-C1` payload shape
(`test_reconcile_builds_payload_with_exactly_the_req_c1_keys` — the key SET must equal
`{source, chain, fill_tid, confirmed, external, earn_usdc, cost_usdc, wallet, task, wake}`
exactly, no more, no fewer) and must advance the checkpoint to the LAST recorded fill's time,
never the first (`test_reconcile_full_successful_batch_checkpoint_is_last_fills_time_not_first`).
Three static greps (embedded directly in `test_reconcile.py` so they run as part of the same
pytest suite, not a separate manual step) close the loop on REQ-D1/D2/D3: no reimplemented
`appendLedger`/`assertOwnIdentityOnly`/`checkHalt`, no second key-loading path
(`_key(`/`resolve-identity` must be absent from `reconcile.py`), and no
`market_close`/`.order(`/`update_leverage` call anywhere in `reconcile.py` (READ-ONLY against
the exchange, per REQ-D3).

## CRIT-004 — structural_integrity

Two structural facts about the EXISTING files this feature modifies (`hl.py`, `run.sh`) are
checked by static grep, embedded in `test_reconcile.py` so a `pytest` run alone (no separate
manual grep step) proves them:

- `test_hl_py_has_no_closed_pnl_usd_field_static_grep` — REQ-A1: the string `closed_pnl_usd`
  must not appear anywhere in `hl.py` post-fix (today it does, at line 147 — this is why this
  test currently FAILS, correctly, in the RED baseline).
- `test_hl_py_cmd_close_json_output_has_no_closed_pnl_usd_key` — the SAME assertion exercised
  through the real `cmd_close` code path with a faked `Exchange`/`Info` (skipped in this
  environment via `pytest.importorskip("hyperliquid")` since the SDK is only installed in
  hl-trade's dedicated `.venv`, not this session's system Python — the static grep above already
  covers REQ-A1 without needing the SDK; this test is the belt-and-suspenders check for whenever
  it DOES run in that venv).
- `test_run_sh_calls_hl_reconcile_before_cooldown_and_close_branch_static_grep` — REQ-E3: the
  line invoking `hl.py ... reconcile` must have a LOWER line number than both the `_hl_since`
  cooldown check and the `ACTION = "close"` branch. `run.sh` doesn't call `reconcile` at all yet,
  so this correctly fails in the RED baseline (`reconcile_line is None`).

## CRIT-005 — verification_readiness

`ledger.mjs`'s hyperliquid disjunct is additive-only by construction: `ledger.test.mjs` is a
BRAND NEW file (never edits `ledger.test.js`), and its own non-regression tests
(`isProfitable: non-regression — ...` ×4) re-run the EXACT same EVM/Solana/narrate/swap fixture
shapes `ledger.test.js` already covers, proving no accidental behavior change leaks in from the
new third disjunct. The RED-phase run of BOTH files in this sprint shows exactly the expected
split: `ledger.test.js` (pre-existing, untouched) is 9/9 green already; `ledger.test.mjs` (new)
is 10/12 green and 2/12 red — the 2 failures (`fill_tid` passthrough absent, hyperliquid
disjunct absent) are the literal REQ-C2/REQ-C3 gap Phase 2b closes; the 10 passes are
non-regression fixtures that were never expected to need new logic.

## CRIT-006 — verification_readiness (live E2E capstone, PROP-021)

Fixture suites alone cannot prove the pipeline computes the CORRECT real-world number — the old
code was ~200x wrong while being internally consistent with its own (wrong) data source. This
criterion makes the Tier-2 live E2E a sprint pass condition, exactly as verification-
architecture.md's Done section requires for strict mode: run the REAL `reconcile()` code path
(no stubs in the pipeline under test) against the live Hyperliquid Info API for the audited
wallet `0xa3cdd4...` (146 real fills at audit time), recording into a SCRATCH ledger + scratch
checkpoint (production ledger and production checkpoint untouched; the scratch paths are the
injectable seams the tests already define). Pass = (a) every `closedPnl != 0` fill recorded
exactly once, cross-checked by count against the raw live response captured in the same run;
(b) `sum(net_usdc)` over recorded lines equals raw `sum(closedPnl - fee)` within 1e-6;
(c) an immediately repeated run appends zero lines (live idempotency); (d) no recorded line or
log line describes its own numbers as dry/fake/mock/simulated. Raw response + transcript are
saved under `evidence/` as the fresh E2E artifact the Phase 3 adversary gate requires.

## Cross-criterion note (contract-review F-4)

PROP-007 is intentionally cited under both CRIT-002 and CRIT-003: checkpoint-advance
correctness is simultaneously an edge-case concern (E2/E4 recovery semantics) and a
composition-root ordering concern. The shared citation is deliberate, not an oversight; each
criterion still has non-overlapping pass conditions beyond it.
