# Implementation Review Findings — hl-realized-pnl (Phase 3, iteration 1)

Reviewer: fresh-context VCSDD adversary, zero builder context. Reviewed behavioral-spec.md,
verification-architecture.md, contracts/sprint-1.md, the full diff (`main...HEAD`, commits
b770f06+630fc93 on top of the RED-phase commit ef7f9ef), all new/modified source files, all new
test files, and evidence/ (independently re-derived, not trusted at face value).

## F-1 — BLOCKING — run.sh's pre-existing explicit-close-record branch still reads the
`closed_pnl_usd` field this feature deletes, silently degrading every real close to a fabricated
$0.00 ledger line

**File**: `skills/earn/run.sh:214-222` (unmodified by this diff — confirmed identical to
`main:skills/earn/run.sh:206-214` via `git show main:skills/earn/run.sh`)

**What**: REQ-A1 removes `closed_pnl_usd` from `hl.py cmd_close`'s JSON output entirely
(confirmed: `grep -n "closed_pnl_usd" skills/earn/hl-trade/hl.py` = 0 matches, PROP-018 passes).
But `run.sh`'s pre-existing `ACTION = "close"` branch — the code path that fires on EVERY explicit
model-issued close, i.e. the single most common way an HL position gets closed — still does:

```bash
RES=$(PKVAR="$PKVAR" "$HLPY" "$HLDIR/hl.py" close "$COIN" 2>&1)
...
PNL=$(printf '%s' "$RES" | python3 -c "import json,sys
try: print(json.load(sys.stdin).get('closed_pnl_usd',0) or 0)
except Exception: print(0)" 2>/dev/null || echo 0)
JSON=$(python3 -c "import json; print(json.dumps({'wallet':'${WLOW:-unknown}','source':'hl-trade',
       'task':'hl-close $COIN','earn_usdc':float('$PNL' or 0),'cost_usdc':0,'wake':'$WAKE'}))" ...)
OUT=$(record_line "$JSON"); echo "[earn] hl close recorded -> $OUT"; exit 0
```

Since `hl.py close`'s JSON no longer has the `closed_pnl_usd` key, `json.load(sys.stdin).get(
'closed_pnl_usd', 0)` now unconditionally returns `0` (no exception is raised — `.get` with a
default silently succeeds). This branch therefore now appends, on **every single explicit HL
close**, a ledger line shaped `{"source":"hl-trade","task":"hl-close ETH","earn_usdc":0.0,
"cost_usdc":0,"wake":"..."}` — no `chain`, no `fill_tid`, no `external` — indistinguishable from a
genuine $0.00 breakeven close.

**Why this is exactly the bug class this feature exists to kill**: REQ-A1 states the false
pre-close number "SHALL NOT be replaced by a relabeled or re-scaled version of the same number."
Functionally, at this call site, that is precisely what happened: the field's silent deletion
converts an inaccurate-but-nonzero number into an unconditional, silent, permanent zero at a call
site nobody re-audited. Tier-0 rationale (e) in verification-architecture.md names exactly this
failure mode: "the fix doesn't actually remove the bug it targets." It doesn't — it moves the same
class of false-number bug from `hl.py` into `run.sh`, at a site this feature's own change directly
caused to regress, and leaves it completely unguarded: **every static check for REQ-A1 (PROP-018)
greps only `hl.py`, never `run.sh`** — verified this is the only file grepped for
`closed_pnl_usd` anywhere in `tests/test_reconcile.py`, the contract, or the verification
architecture. No REQ, PROP, EDGE case, or test in this feature's entire verification architecture
addresses `run.sh`'s own consumption of the field it deletes.

**Concrete failure scenario**: Model issues `action:"close"` for an open ETH position that
actually closed with real P&L (say +$1.20 realized, per Hyperliquid's own settled fill). This wake:
1. `reconcile()` runs FIRST (per REQ-E3) — finds no new fill yet, since the close hasn't executed
   yet this wake. Records 0.
2. The `ACTION="close"` branch executes `hl.py close ETH` (real `market_close`, real money moves).
3. The now-broken `PNL` extraction silently yields `0`. A spurious line
   `{"task":"hl-close ETH","earn_usdc":0.0,"cost_usdc":0}` is appended — permanently, forever, for
   every future explicit close, not a one-time bug.
4. The NEXT wake, `reconcile()` correctly picks up the real settled fill and records the TRUE
   number under a *different* task label (`"hl-close ETH tid=<real tid>"`), with `external:true`,
   `chain`, `fill_tid`.
5. Net effect: the ledger now carries TWO lines per real close — a misleading fabricated $0.00 one
   immediately, and the true one a wake later — doubling HL ledger volume relative to real close
   events and creating a trap for any human/dashboard/self-improve consumer that reads
   `task startswith "hl-close"` lines expecting one line per close to reflect that close's outcome.

**Money-safety scope**: this does NOT bypass GATE-0 (the spurious line's `net_usdc == 0` so
`isProfitable` correctly returns false), and does NOT cross instance boundaries. It is a
*silent, permanent, unguarded data-integrity regression this feature's own change directly causes*
in a file this feature already modifies (`run.sh`) — a real code, real trades, real ledger, wrong
number, nobody-notices class of defect on a real mainnet trading rail.

**Fix required before this can be Done**: either (a) delete this branch's own dead PNL-recording
logic entirely (the reconciler now owns 100% of HL realized-P&L recording, including the
next-wake pickup of an explicit close's own fill — this branch's separate `record_line` call for
`hl-close $COIN` is now redundant with what `reconcile()` will do next wake and should simply stop
recording an `earn_usdc`/`cost_usdc` line at all, or narrate-only), or (b) add a REQ + PROP + test
asserting `run.sh` no longer references `closed_pnl_usd` anywhere (not just in `hl.py`), with the
branch's behavior explicitly specified. Leaving it as literal dead code that now always evaluates
to `0` and gets recorded as if it were a real value is not acceptable for money-recording code on a
real mainnet rail.

---

## Verification of claims that DID hold up (no findings, cross-checked independently)

- **Test suites, run live in this review**: `skills/earn/hl-trade` pytest: **39 passed, 1 skipped**
  (matches contract's expected 39+1skip exactly — the 1 skip is
  `test_hl_py_cmd_close_json_output_has_no_closed_pnl_usd_key`, correctly skipped via
  `pytest.importorskip("hyperliquid")` in this environment). `skills/earn/self-improve` pytest:
  **44 passed**. `ledger.test.mjs`: **12 passed, 0 failed**. Pre-existing `ledger.test.js`:
  **9 passed, 0 failed** (unmodified, non-regression confirmed).
- **PROP-021 live E2E, independently re-derived from the raw evidence** (not trusted from the log):
  parsed `evidence/prop-021-userfills-live-raw.json` — 146 total fills, 71 with `closedPnl != 0`,
  `sum(closedPnl - fee)` over those 71 = `0.081756`. Parsed
  `evidence/prop-021-scratch-ledger.jsonl` — 71 lines, 71 unique `fill_tid`s, `sum(net_usdc)` =
  `0.08175599999999998` (matches to float noise, well within 1e-6). All 71 lines carry
  `chain:"hyperliquid"`, `confirmed:true`, `external:true`, and the same wallet
  (`0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21`). No "dry/fake/mock/simulated" anywhere in the
  scratch ledger. This capstone is honestly derived, not fabricated or rounded to look better.
- **Static-grep proof obligations**, re-run directly (not trusted from pytest's own report):
  PROP-015 (`appendLedger`/`assertOwnIdentityOnly`/`checkHalt` absent, `record.mjs` present),
  PROP-016 (`_key(`/`resolve-identity` absent from `reconcile.py`; `cmd_reconcile` calls
  `_clients()`), PROP-017 (`market_close`/`.order(`/`update_leverage` absent from `reconcile.py`),
  PROP-018 (`closed_pnl_usd` absent from `hl.py`), PROP-019 (reconcile invocation at `run.sh:177`,
  strictly before both the cooldown check at `run.sh:205-206` and the close branch at
  `run.sh:214`), PROP-010 (`since_time_ms + 1` and unbounded `.user_fills(` both absent from
  `reconcile.py`), PROP-023 (`.blockrun`/`.anicca`/`.openclaw`/`/Users/` all absent from
  `reconcile.py`) — all confirmed clean by direct grep, matching the tests' own claims.
- **REQ-B8 inclusive-boundary money-safety capstone** (F-1 from the earlier spec-review adversary):
  `reconcile.py` passes the raw `since_time_ms` unchanged (no `+1`) to `user_fills_by_time`;
  `PROP-010b`'s two-pass tied-timestamp integration test genuinely exercises this (verified by
  reading the test body, not just its name) and would fail against a strictly-greater-than
  implementation.
- **REQ-B10 concurrency lock**: verified `reconcile()`'s lock is acquired first, held across the
  entire read-check-record-write sequence, and released in a `finally` regardless of STOP/error
  path; `PROP-022`'s test uses a REAL `fcntl.flock` (not a fake) and asserts zero fetch calls when
  locked — genuinely falsifiable.
- **Purity boundary**: `fills.py` has no I/O; `reconcile.py`'s `plan_batch` is pure and separated
  from the effectful loop exactly as verification-architecture.md specifies.
- **`_recorded_tids_cache`** (module-level dict in `reconcile.py`, not mentioned in the original
  verification architecture): reviewed for correctness — it is keyed by `ledger_path`, only ever
  adds to the authoritative disk-scan result (never the sole source), and the module's own
  docstring correctly identifies that in production `hl.py reconcile` runs as a fresh CLI
  subprocess every wake, making this cache inert there. Confirmed harmless; not a finding.
- **P1 HALT guard precedence** (REQ-E3's stated non-override): `earn-guard.mjs` check sits at
  `run.sh:85`, unconditionally before the `STRATEGY="hl"` block (~`run.sh:172+`) — confirmed the
  guard still takes precedence exactly as REQ-E3 states.
- **ledger.mjs additive-only change**: `isProfitable`'s new `hlOk` disjunct is a pure `||` addition;
  `deriveLine`'s `fill_tid` passthrough follows the exact same conditional-key pattern as
  `tx`/`sig`/`chain`. Re-ran the pre-existing `ledger.test.js` fixtures unmodified — all 9 still
  green.

## Minor / notes (non-blocking)

- **N-1** (note): `_build_payload`'s `task` string (`f"hl-close {coin} tid={tid}".strip()`) will
  render as `"hl-close  tid=42"` (double space) if `fill.get("coin", "")` is ever empty — cosmetic
  only, `.strip()` only trims the ends, not the internal double space. Live evidence shows `coin`
  is always populated in practice (`"ETH"` on all 71 recorded fills), so this is theoretical.
- **N-2** (note): `is_unprocessable`'s `tid` check happens in `plan_batch` AFTER the
  already-recorded-tid dedup check, and Python's `True in {1}` is `True` (bool/int identity) — a
  fill with `tid: True` would be misclassified as a duplicate of a real `tid: 1` before
  `is_unprocessable`'s own bool-rejection ever runs. This cannot occur with real Hyperliquid API
  data (`tid` is always a genuine large integer, never a JSON boolean), so this is not a practical
  risk, just a theoretical type-coercion quirk worth a one-line comment if ever revisited.
