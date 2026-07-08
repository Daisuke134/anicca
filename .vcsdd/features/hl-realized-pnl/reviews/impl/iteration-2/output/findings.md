# Implementation Review Findings — hl-realized-pnl (Phase 3, iteration 2)

Reviewer: fresh-context VCSDD adversary, zero knowledge of prior reviewers' reasoning. Reviewed
behavioral-spec.md (incl. REQ-A3/EDGE-12 added at impl-review iteration 1), verification-
architecture.md (30 PROPs incl. PROP-024), contracts/sprint-1.md, the full diff
(main...HEAD, commits b770f06+630fc93+486bef6), iteration-1's findings.md, all source/test
files in the worktree, and evidence/ — all claims independently re-derived from raw data, not
trusted at face value.

## No BLOCKING findings.

## F-1 (iteration-1) verification: genuinely fixed, not cosmetically patched

Iteration-1 found that skills/earn/run.sh's ACTION="close" branch kept reading the
closed_pnl_usd field REQ-A1 deletes from hl.py's JSON output, so .get('closed_pnl_usd', 0)
silently degraded to 0 and got recorded as a real ledger line on every explicit HL close —
doubling ledger volume with a fabricated $0.00 line ahead of the reconciler's true one a wake
later.

Re-verified directly against `git diff main...HEAD -- skills/earn/run.sh`: the fix is a clean
DELETION, not a relabel. The old branch computed PNL from closed_pnl_usd, built a JSON payload
with 'earn_usdc':float(PNL), and called record_line. It is now:

```
if [ "$ACTION" = "close" ] && [ -n "$POS" ]; then
  RES=$(PKVAR="$PKVAR" "$HLPY" "$HLDIR/hl.py" close "$COIN" 2>&1)
  date +%s > "$HL_LAST" 2>/dev/null || true
  echo "[earn] hl close $COIN -> $RES"
  exit 0
fi
```
(skills/earn/run.sh:220-225). No closed_pnl_usd, no PNL=, no record_line call anywhere in this
branch — confirmed by direct read, not grep alone. `grep -n "closed_pnl_usd" skills/earn/run.sh`
= 0 matches (re-run, matches PROP-024's claim). This is fix option (a) from iteration-1's own
finding ("delete this branch's own dead PNL-recording logic entirely") — applied exactly. Two
NEW tests lock this in permanently: test_run_sh_never_references_closed_pnl_usd_anywhere and
test_run_sh_close_branch_never_calls_record_line_for_its_own_pnl_line
(skills/earn/hl-trade/tests/test_reconcile.py:630-667) — read both test bodies; the second
correctly disambiguates the close EXECUTION branch (gated on -n "$POS") from the anti-churn
cooldown guard's compound condition (which also contains the substring ACTION" = "close") via
its -n "$POS" co-occurrence check — not a naive substring match that could pass vacuously. Both
tests are genuinely falsifiable: they would fail against the pre-iteration-1 code.

Verdict: F-1 is completely and correctly fixed. No trace of the bug class remains.

## New-edge hunt (no findings)

- Other run.sh consumers of hl.py close's JSON output: grepped the full file for
  closed_pnl|unrealizedPnl|uPnL|pnl — only two matches, neither a bug: (1) uPnL at run.sh:190,
  used exclusively to build a human-readable POS narrate string for the hl-observe task label,
  never fed into earn_usdc/cost_usdc (that record call hardcodes 'earn_usdc':0,'cost_usdc':0,
  consistent with REQ-E1); (2) a code comment. No other call site reads a pnl-shaped field out
  of hl.py's JSON and records it as revenue.
- set -e interaction: run.sh uses set -u only (confirmed via grep -n "^set "), not set -e. The
  RECON=$(... hl.py reconcile ... 2>&1) call's exit code is never checked, so a non-zero exit
  from reconcile cannot abort the wake early — consistent with REQ-B9's "never raises to caller"
  contract.
- Fabricated-$0 class elsewhere: open/hl-cooldown/hl-observe/hl-fund-skipped all hardcode
  earn_usdc:0/cost_usdc:0 literally (never derived from a stale/misread field) — honest zeros,
  not a fabricated non-zero-turned-zero bug. Diff confirms these four blocks are byte-identical
  to main (PROP-020, re-verified via git diff — only additive hunks around the reconcile call
  and the close-branch deletion; no line inside these four blocks appears in the diff at all).

## Independent re-derivation of PROP-021 (live E2E capstone)

Parsed evidence/prop-021-userfills-live-raw.json directly (not the log's summary): 146 total
fills, 146 unique tids, 71 with closedPnl != 0, sum(closedPnl - fee) over those 71 = 0.081756.
Parsed evidence/prop-021-scratch-ledger.jsonl directly: 71 lines, 71 unique fill_tids (matches
count exactly, zero drops/dupes), sum(net_usdc) = 0.08175600000000001 (matches within float
noise, well under 1e-6), all 71 lines carry chain=="hyperliquid"/confirmed==true/external==true
and the same wallet address, zero "dry/fake/mock/simulated" occurrences anywhere in the file.
This independently reproduces every number in evidence/prop-021-live-e2e.log's own claimed
verdict — not merely trusted from the log text.

Noted (not a finding against this feature): the E2E log itself documents that
assertOwnIdentityOnly (shared identity-guard.mjs, out of this feature's diff) gates only on
env-PII patterns and the source allowlist, not on the ledger line's wallet field — so a run
against a non-current-instance wallet (the rotated 0xa3cdd4... address) went through record.mjs
cleanly with no HALT. This is pre-existing shared infrastructure this feature correctly reuses
via REQ-D1 rather than reimplementing (the spec explicitly forbids reimplementing
assertOwnIdentityOnly); it is not something this feature's diff introduces, worsens, or is in
scope to fix. Flagging only as a pointer for a future cross-cutting identity-guard hardening
feature, not a finding against hl-realized-pnl.

## Test suites — run live in this review (fresh evidence)

- skills/earn/hl-trade pytest: 41 passed, 1 skipped (the skip is
  test_hl_py_cmd_close_json_output_has_no_closed_pnl_usd_key, correctly gated on
  pytest.importorskip("hyperliquid") — SDK not installed in this session's system Python).
  Cross-checked the test count: grep -oE "def test_" test_reconcile.py = 31 tests,
  test_fills.py = 11 tests, 31+11=42 total = 41 passed + 1 skipped. Matches.
- skills/earn/self-improve pytest: 44 passed (ran directly via python -m pytest, bypassing a
  local pytest-binary shell-wrapper issue unrelated to this feature).
- skills/_shared/lib/__tests__/ledger.test.mjs: 12 passed, 0 failed (node --test).
- Pre-existing skills/_shared/lib/__tests__/ledger.test.js: 9 passed, 0 failed, confirmed
  byte-unmodified by git diff main...HEAD (no diff hunk touches this file at all).

## Structural greps — re-run directly, not trusted from pytest's own report

All clean (0 matches for forbidden patterns, >=1 for required patterns), matching every PROP
claim:
- PROP-015 (D1): appendLedger|assertOwnIdentityOnly|checkHalt absent from reconcile.py;
  record.mjs referenced.
- PROP-016 (D2): _clients() used by every hl.py subcommand incl. cmd_reconcile; _key( /
  resolve-identity absent from reconcile.py.
- PROP-017 (D3): market_close|.order(|update_leverage absent from reconcile.py.
- PROP-018 (A1): closed_pnl_usd absent from hl.py.
- PROP-019 (E3): hl.py ... reconcile at run.sh:177, strictly before the cooldown check
  (run.sh:205-206) and the close-action branch (run.sh:220) — line-number ordering confirmed.
- PROP-023 (D4): .blockrun|.anicca|.openclaw|/Users/ absent from reconcile.py; checkpoint/
  ledger paths in hl.py::cmd_reconcile derived exclusively from os.path.dirname(__file__)
  (here), never a literal foreign path.
- PROP-024 (A3, this iteration's focus): closed_pnl_usd absent from run.sh; the isolated
  ACTION="close" execution branch contains no record_line call.

## Purity / composition-root correctness (re-read, not re-trusted)

plan_batch in reconcile.py correctly implements REQ-B4's ordering: dedup check (tid in
already_recorded_tids) BEFORE the is_unprocessable STOP check, exactly as REQ-B4.1 →
REQ-B4.2 requires. reconcile()'s composition root acquires the lock first (returns immediately,
touching nothing, if held), reads the checkpoint, fetches with the raw since_time_ms (no +1),
plans, executes record attempts in order (breaking the loop on the first record_line_fn
exception per REQ-B4.3), advances the checkpoint to the last handled-or-recorded fill's time
only if at least one fill was handled, and releases the lock in a finally regardless of outcome.
Read the PROP-010b tied-timestamp two-pass test
(test_tied_timestamp_partial_stop_recovers_the_sibling_fill_on_the_next_pass,
test_reconcile.py:337-364) and the PROP-022 concurrency-lock tests
(test_acquire_lock_second_caller_gets_none_while_first_holds_it,
test_reconcile_returns_locked_status_and_touches_nothing_when_lock_held,
test_reconcile.py:545-577) body-by-body: both are genuine, non-vacuous, and use a real
fcntl.flock (not a fake) for the lock test — confirmed by direct read.

ledger.mjs's fill_tid passthrough (deriveLine) and hlOk disjunct (isProfitable) are minimal,
additive if/|| insertions — re-read the whole file; no existing line changed shape.

REQ-C4's follow-up comment in skills/earn/self-improve/lib/ledger_reader.py is a 4-line
comment-only addition (confirmed via git diff) — no behavior change, matches the spec's explicit
"documented follow-up, NOT implemented" instruction exactly.

## Minor / notes (non-blocking, carried forward from iteration 1, still present, still cosmetic)

- N-1: _build_payload's task string would render with a double space ("hl-close  tid=42") if
  fill.get("coin", "") were ever empty — theoretical, live evidence shows coin always populated.
- N-2: is_unprocessable's tid int-check runs in plan_batch after the already-recorded-tid dedup
  check; Python's True in {1} quirk means a hypothetical tid: True would misclassify as a
  duplicate before is_unprocessable ever runs. Real Hyperliquid tid values are always large
  genuine integers — this cannot occur with live data.

Neither N-1 nor N-2 is money-affecting or reachable with real Hyperliquid API data; both are
carried forward unresolved from iteration 1 with no change in severity.
