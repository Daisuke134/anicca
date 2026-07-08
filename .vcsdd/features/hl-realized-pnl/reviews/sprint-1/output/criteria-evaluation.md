# Sprint 1 Convergence Grading — hl-realized-pnl — Criteria Evaluation

Fresh-context adversary review. All checks below were re-run independently this session (fresh
scratch venv at `/private/tmp/.../scratchpad/hl-adversary-verify/.venv`, fresh `node --test`
invocations, fresh parsing of the raw live-E2E JSON) — no evidence was taken on faith from
`verification-report.md` without an independent re-derivation.

## Findings register

- **FIND-001** (minor, non-blocking): CRIT-001's `passThreshold` text in
  `contracts/sprint-1.md` says "`test_fills.py`'s 12 tests all pass". The actual file has 11
  `def test_` functions (`grep -c "^def test_" tests/test_fills.py` = 11), and all 11 pass. Every
  named property (PROP-001 x3, PROP-002, PROP-002b, PROP-003 x5) plus the ascending-sort test is
  present and green — there is no missing coverage, just a miscounted number in the contract's
  prose. Does not change the criterion's pass/fail outcome.
- **FIND-002** (minor, non-blocking, contract-authoring nit): `contracts/sprint-1.md`'s own YAML
  frontmatter labels CRIT-005's `dimension:` as `implementation_correctness`, but the markdown
  body's own section header for the same criterion reads `## CRIT-005 — verification_readiness`.
  This review used the YAML frontmatter (the structured/parseable source) to bucket CRIT-005
  under `implementation_correctness` in the verdict. Either bucketing is defensible given the
  criterion's actual content (an implementation-correctness claim — additive-only diff — verified
  via a verification-readiness artifact — a new test file); this is purely a labeling
  inconsistency internal to the contract document, not a functional gap.

No blocking or major findings were identified. `findingCount` in the verdict = 0
(blocking+major); `previousFindingCount` = 1, taken from `reviews/impl/iteration-1/output/verdict.json`'s
`blockingFindings:1, majorFindings:0` (the F-1 fabricated-$0.00-line defect, fixed in iteration-2
and confirmed still fixed by this review's own re-run of PROP-024's tests below).

---

## CRIT-001 — spec_fidelity

**Check performed:** built a fresh scratch venv (`python3 -m venv` + `pip install pytest
hypothesis`), ran `python3 -m pytest tests/test_fills.py -v` against
`skills/earn/hl-trade/tests/test_fills.py` in the worktree at HEAD `486bef6`.

**Result:** 11/11 PASS (0 failed, 0 skipped):
`test_compute_realized_pnl_win_charges_fee_against_earn_only`,
`test_compute_realized_pnl_loss_folds_fee_into_cost`,
`test_compute_realized_pnl_exact_breakeven_still_charges_fee`,
`test_select_close_fills_excludes_zero_pnl_and_time_strictly_before_since`,
`test_select_close_fills_boundary_is_inclusive_not_exclusive`,
`test_select_close_fills_sorts_ascending_by_time_even_if_input_is_unsorted`,
`test_is_unprocessable_true_for_non_numeric_closed_pnl`,
`test_is_unprocessable_true_for_missing_fee`, `test_is_unprocessable_true_for_missing_tid`,
`test_is_unprocessable_true_for_non_integer_tid`,
`test_is_unprocessable_false_for_well_formed_live_hl_api_shape`.

Also read `lib/fills.py` directly: `select_close_fills` filters on `f.get("time", -1) >=
since_time_ms` — the `>=` (not `since_time_ms + 1`) is the actual inclusive-boundary
implementation the PROP-002b test guards against regressing.

**Verdict: PASS** (see FIND-001 for the 12-vs-11 count discrepancy, non-blocking).

## CRIT-002 — edge_case_coverage

**Check performed:** same pytest run extended to `tests/test_reconcile.py`; additionally read the
full body of `test_tied_timestamp_partial_stop_recovers_the_sibling_fill_on_the_next_pass`
(lines 337-364) to confirm the PROP-010b assertions match the contract's literal description,
not just the test's name.

**Result:** All cited tests PASS:
`test_reconcile_never_calls_record_line_fn_for_an_already_recorded_tid` (REQ-B4.1),
`test_plan_batch_stops_at_first_unprocessable_fill_and_never_plans_past_it` +
`test_reconcile_checkpoint_stops_before_unprocessable_fill_t3_never_attempted` (REQ-B4.2),
`test_reconcile_stops_batch_when_record_line_fn_raises_on_second_fill` (REQ-B4.3),
`test_tied_timestamp_partial_stop_recovers_the_sibling_fill_on_the_next_pass` (PROP-010b) —
verified line-by-line: pass 1 stops after `tid=2` raises, checkpoint lands on `500`; pass 2
asserts `info.calls[1]["since_time_ms"] == 500` (inclusive re-query, not 501) and
`[p["fill_tid"] for p in pass2_stub.calls] == [2, 3]` (X/tid=1 skipped as duplicate, Y/tid=2
recorded, Z/tid=3 recorded normally), checkpoint advances to `600`. This is an exact match to
the contract's prose description.
Also PASS: `test_reconcile_api_error_returns_status_and_leaves_checkpoint_untouched` (REQ-B9),
`test_acquire_lock_second_caller_gets_none_while_first_holds_it` +
`test_reconcile_returns_locked_status_and_touches_nothing_when_lock_held` (REQ-B10).

**Verdict: PASS.**

## CRIT-003 — implementation_correctness

**Check performed:** read `lib/reconcile.py` end-to-end (`_build_payload` at lines 143-153,
`reconcile()` composition root at lines 175-215). Independently re-ran the static greps rather
than trusting the pytest static-grep tests alone:
`grep -nE "appendLedger|assertOwnIdentityOnly|checkHalt" lib/reconcile.py` (0 matches),
`grep -nF "_key(" lib/reconcile.py` (0 matches),
`grep -nF "resolve-identity" lib/reconcile.py` (0 matches),
`grep -nE "market_close|\.order\(|update_leverage" lib/reconcile.py` (0 matches),
`grep -nF "record.mjs" lib/reconcile.py` (3 matches — the delegation itself).

**Result:** `_build_payload` returns exactly
`{source, chain, fill_tid, confirmed, external, earn_usdc, cost_usdc, wallet, task, wake}` — 10
keys, no more, no fewer, matching REQ-C1 exactly (PROP-012 PASS in the pytest run). `reconcile()`
orders: `acquire_lock` -> `read_checkpoint` -> `info.user_fills_by_time` (fetch) ->
`select_close_fills`/`plan_batch` -> per-step dedup/record loop -> `write_checkpoint` — this is
REQ-B4-through-B6 in the contractually-required order. `last_handled_time` is updated on BOTH
`skip_duplicate` and `record` actions (not only on record), so the checkpoint always advances to
the time of the LAST fill *handled* in the batch, never the first attempted one — confirmed
against `test_reconcile_full_successful_batch_checkpoint_is_last_fills_time_not_first` (PASS).
`ledger.mjs`'s diff (re-pulled with `git diff f89f37c..486bef6 -- skills/_shared/lib/ledger.mjs`
this session) shows the pre-existing `evmOk`/`solOk` lines byte-identical; only a new `hlOk`
line is added and OR'd into the return — additive-only construction confirmed at the diff level,
not just by test outcome. `ledger.test.mjs` (12/12 fresh `node --test` run) and pre-existing
`ledger.test.js` (9/9 fresh run, unmodified) both PASS.

**Verdict: PASS** (see FIND-002 for the contract's internal dimension-label inconsistency for
CRIT-005, non-blocking, resolved by using the YAML frontmatter as canonical).

## CRIT-004 — structural_integrity

**Check performed:** `grep -nF "closed_pnl_usd" skills/earn/hl-trade/hl.py` (independently
re-run); installed `hyperliquid-python-sdk` + `eth_account` into the same scratch venv and
re-ran `test_hl_py_cmd_close_json_output_has_no_closed_pnl_usd_key` (this test was SKIPPED in the
ambient ~11/41 ecosystem run for lack of the SDK); re-derived the `run.sh` line-number ordering
independently.

**Result:** `closed_pnl_usd` — 0 matches anywhere in `hl.py` (REQ-A1 confirmed at the file level,
not just via the static-grep test). With the SDK installed, the previously-skipped test now
executes and PASSES, independently reproducing the Phase 5 verification-report.md's claim that
this coverage gap closes once the SDK is present. `run.sh` line numbers: `hl.py ... reconcile`
call at line 177; `_hl_since=` cooldown computation at line 205; `ACTION = "close"` branch
references at lines 206 and 220. `177 < 205` and `177 < 206/220` both hold — `hl.py reconcile` is
wired in before both the cooldown check and the close-action branch on every `STRATEGY=hl` wake,
matching REQ-E3.

**Verdict: PASS.**

## CRIT-005 — verification_readiness (per markdown section header) / implementation_correctness
(per YAML frontmatter — see FIND-002)

**Check performed:** confirmed `ledger.test.mjs` is a genuinely NEW file (not an edit to
`ledger.test.js`) via the commit diff-stat (`ledger.test.mjs | 123 +++++`, pure addition, no
corresponding deletion against `ledger.test.js`); ran both test files fresh with `node --test`.

**Result:** `ledger.test.mjs` 12/12 PASS (PROP-013 `fill_tid` passthrough x2, PROP-014a-e HL
win/loss-rejected/missing-external-rejected/malformed-rejected x2/non-regression x4).
`ledger.test.js` (pre-existing) 9/9 PASS, file untouched by this feature's commits (confirmed via
`git diff f89f37c..486bef6 -- skills/_shared/lib/__tests__/ledger.test.js` producing no output —
the file does not appear in the diff at all).

**Verdict: PASS.**

## CRIT-006 — verification_readiness (live E2E capstone, PROP-021)

**Check performed:** did NOT take the verification-report.md's numbers on faith. Independently
parsed `evidence/prop-021-userfills-live-raw.json` (the raw live Hyperliquid API response) with a
fresh `python3` one-liner: counted total fills, counted `closedPnl != 0` fills, summed
`closedPnl - fee` over those. Independently parsed
`verification/prop-021-phase5-scratch-ledger.jsonl` with a second fresh `python3` one-liner:
counted lines, counted unique `fill_tid` values, summed `earn_usdc - cost_usdc`. Ran
`grep -iE "dry|fake|mock|simulated"` across the scratch ledger and both phase5 rerun logs.

**Result:**
- Raw API response: 146 total fills, 71 with `closedPnl != 0`, `sum(closedPnl - fee)` over those
  71 = **0.081756** (computed fresh from the raw JSON — not copied from the log or report).
- Scratch ledger: 71 lines, 71 unique `fill_tid` values (zero duplicates, zero drops — count
  matches the raw 71 nonzero fills exactly), `sum(earn_usdc - cost_usdc)` = **0.081756** — exact
  match to the raw-derived sum, well within the 1e-6 tolerance (exact match, not merely close).
- Pass 2 (idempotency): the phase5 rerun log shows `{"status":"ok","recorded":0}` for pass 2 with
  checkpoint carried over from pass 1 (`1783370643509`); scratch ledger line count is unchanged
  at 71 after pass 2.
- `grep -iE "dry|fake|mock|simulated"` — 0 matches across all three files checked.
- No signing key / `Exchange` object construction found anywhere in the E2E logs (read-only
  `Info(...)` client only).

**Verdict: PASS** — this is the strongest-evidenced criterion in the sprint: every number was
independently re-derived from the raw artifact, not merely re-read from a prose claim.

---

## Overall

6/6 criteria evaluated, 6/6 PASS, 0 blocking findings, 0 major findings, 2 non-blocking
documentation nits (FIND-001, FIND-002) recorded for the contract author's awareness but not
gating this sprint's convergence.

**Sprint 1 overall verdict: PASS.**
