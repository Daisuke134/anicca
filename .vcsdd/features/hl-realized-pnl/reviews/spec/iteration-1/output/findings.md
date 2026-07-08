# Spec Review Findings — hl-realized-pnl (Phase 1c, iteration 1)

Reviewer: fresh-context VCSDD adversary. Reviewed `specs/behavioral-spec.md` and
`specs/verification-architecture.md` against the referenced production code
(`skills/earn/hl-trade/hl.py`, `skills/earn/run.sh`, `skills/_shared/lib/ledger.mjs`,
`skills/earn/lib/record.mjs`, `skills/earn/lib/resolve-identity.mjs`,
`skills/earn/sol-trade/lib/record-swap.mjs`), plus the installed `hyperliquid-python-sdk`
(v0.24.0) source and the live `earn-ledger.jsonl` for the current wallet.

## F-1 — BLOCKING

**Severity**: BLOCKING
**Dimensions**: spec_fidelity, verification_readiness
**Target REQ/section**: REQ-B5, REQ-B8, REQ-B4.2/B4.3, EDGE-9, NFR-1, PROP-021(a)

**What is wrong**: REQ-B8 fixes the re-query boundary at `since_time_ms + 1` (strictly greater
than the checkpoint), and REQ-B5 sets the checkpoint to "the `time` of the LAST fill it
successfully recorded or confirmed-as-already-recorded... in strict time order." This design
implicitly assumes each candidate fill has a *unique* `time` value. EDGE-9 explicitly says the
opposite is a real, expected case: "A single close produces MULTIPLE partial fills (crossing
several resting orders)" — Hyperliquid's matching engine can and does emit multiple fills for
one order at the identical millisecond timestamp.

Concrete failure trace: candidates sorted ascending are `[X(t=500,tid=1), Y(t=500,tid=2),
Z(t=600,tid=3)]`. Pass 1: `X` records successfully. `Y` is attempted next and its `record_line`
call fails (REQ-B4.3) → the batch STOPS. Per REQ-B5 the checkpoint advances to the time of the
last successfully recorded fill, i.e. `X`'s time = 500. Pass 2 queries
`user_fills_by_time(address, 500 + 1, now, ...)` = `since_time_ms=501` — this strictly excludes
`time == 500`, so `Y` (never recorded, tid=2) can NEVER be fetched again by any future pass. `Y`'s
real closedPnl/fee is silently and permanently dropped from the ledger forever, with no error, no
log, no retry — indistinguishable from a healthy pass that had nothing to record.

This directly contradicts the feature's own explicit invariants: REQ-B9 ("the next wake's
reconcile retries the same window" — false here, the window is gone), NFR-1 ("SHALL NOT silently
drop fills"), and PROP-021(a) ("zero silent drops, zero fabricated extras" verified by count
against live data). This is exactly the "checkpoint corruption" / "silently-wrong money numbers"
failure class this review was asked to hunt for.

The `+1` boundary optimization (REQ-B8) buys nothing in practice — REQ-B4.1's tid-based
idempotency check already makes re-fetching a slightly wider window (inclusive of the checkpoint
fill itself) fully safe and correct, since any already-recorded fill in that window is skipped by
tid, not by time.

**Evidence (file:line)**:
- `.vcsdd/features/hl-realized-pnl/specs/behavioral-spec.md:96-101` (REQ-B5)
- `.vcsdd/features/hl-realized-pnl/specs/behavioral-spec.md:109-114` (REQ-B8, the `+1` boundary)
- `.vcsdd/features/hl-realized-pnl/specs/behavioral-spec.md:84-95` (REQ-B4, stop-at-first-failure)
- `.vcsdd/features/hl-realized-pnl/specs/behavioral-spec.md:222` (EDGE-9, acknowledges same-close multi-fill case)
- `.vcsdd/features/hl-realized-pnl/specs/verification-architecture.md:58,61-63` (PROP-002/005/007 all use distinct t1/t2/t3, none tests a tie)

**Suggested fix (non-binding)**: change REQ-B8's boundary to `since_time_ms` (inclusive, not
`+1`) and rely exclusively on REQ-B4.1's tid-dedup to skip fills already recorded in a prior
pass. Add a PROP for the tied-timestamp + partial-STOP scenario.

## F-2 — MAJOR

**Severity**: major
**Dimension**: spec_fidelity
**Target REQ/section**: REQ-B4.1, REQ-B6, REQ-B9; verification-architecture.md purity/impurity table

**What is wrong**: The dedup mechanism (`already_recorded_tids` read of the ledger, then
conditionally `record_line`) is a check-then-act pattern with no lock. If two `hl.py reconcile`
invocations ever ran concurrently for the same instance, both could read the ledger before
either has appended, both compute the same candidate set, and both attempt to record the SAME
fill — `appendLedger` is a raw `fs.appendFile` with nothing preventing a duplicate line for the
same `tid` under that race. The spec is careful about crash-safety (atomic checkpoint write,
crash-retry idempotency) but never states a "single in-flight invocation per instance" precondition
and adds no lock.

**Evidence (file:line)**:
- `.vcsdd/features/hl-realized-pnl/specs/behavioral-spec.md:84-95` (REQ-B4, no concurrency mention)
- `.vcsdd/features/hl-realized-pnl/specs/behavioral-spec.md:102-105` (REQ-B6, atomic write addresses crash only, not concurrency)
- `skills/_shared/lib/ledger.mjs:69-73` (`appendLedger`: plain `fs.appendFile`, no lock)

**Recommendation**: state explicitly as a precondition/NFR that reconcile is assumed
non-concurrent (enforced by the caller/loop scheduler), or add a file lock (`flock`) around the
read-check-record-write sequence.

## F-3 — MAJOR

**Severity**: major
**Dimension**: spec_fidelity
**Target REQ/section**: REQ-C1 (rationale paragraph), REQ-C3

**What is wrong**: `ledger.mjs` defines GATE-0 as requiring "EXTERNAL revenue: an inbound USDC
transfer to our wallet from a counterparty" and explicitly excludes same-wallet swaps because "a
same-wallet asset rotation proves nothing about a counterparty." `sol-trade/lib/record-swap.mjs`
reinforces this by deliberately never setting `external: true`. REQ-C1 argues a Hyperliquid perp
close differs because it's cash-settled by the exchange's clearinghouse against a counterparty on
the order book — technically true, but it is still a speculative, leveraged, own-capital
directional bet, not revenue for delivered work (0xwork) or a product sale (x402). Treating a
favorable-variance HL close as "proven external revenue" for the same GATE-0 that certifies
"someone paid us for something" is a substantive redefinition of GATE-0's meaning, bundled inside
a spec framed as a recording-bug fix. It also opens a theoretical wash-trading/self-dealing
surface given the multi-instance colony architecture (each instance can have its own HL wallet).

**Evidence (file:line)**:
- `skills/_shared/lib/ledger.mjs:36-47` (GATE-0 doctrine + swap exclusion rationale)
- `skills/earn/sol-trade/lib/record-swap.mjs:1-13,48-52` (precedent: same-wallet trade never sets external:true)
- `.vcsdd/features/hl-realized-pnl/specs/behavioral-spec.md:122-139` (REQ-C1 and its rationale paragraph)

**Recommendation**: not necessarily wrong (the spec surfaces its own reasoning for adversarial
review, as intended), but this should be explicitly confirmed as an intended GATE-0 policy change
by whoever owns that policy, not treated as an implicit side effect of "fixing a bug."

## F-4 — MINOR

**Severity**: minor
**Dimension**: spec_fidelity
**Target REQ/section**: behavioral-spec.md §2 items 1–2

**What is wrong**: The audited real numbers cited ("146 real fills", "actual realized net ≈
−$0.1237 ... versus ≈ −$0.0006 recorded — ~200x under-magnitude") have no evidence artifact
(raw API response, log, fixture) anywhere under `.vcsdd/features/hl-realized-pnl/` or
`skills/earn/hl-trade/` that I could find. Not blocking because PROP-021's live E2E re-derives
real numbers directly from the live API during Phase 5 hardening.

**Evidence (file:line)**: `.vcsdd/features/hl-realized-pnl/specs/behavioral-spec.md:23-29` (§2
items 1-2, the unsubstantiated figures); searched `.vcsdd/features/hl-realized-pnl/` and
`skills/earn/hl-trade/` recursively for any matching raw fill data, found none.

## F-5 — MINOR

**Severity**: minor
**Dimension**: spec_fidelity
**Target REQ/section**: REQ-A2, REQ-B1, REQ-B3, REQ-C1 (all assume `fill.fee` / `fill.tid` exist)

**What is wrong**: The installed `hyperliquid-python-sdk` v0.24.0's own docstring for
`user_fills`/`user_fills_by_time` lists the return shape as `{closedPnl, coin, crossed, dir,
hash, oid, px, side, startPosition, sz, time}` — it does not mention `fee` or `tid` at all. Very
likely a stale/incomplete SDK docstring (Hyperliquid's real API is documented elsewhere to
include these fields), but the entire fee/tid-dependent design (REQ-B1, REQ-B3, REQ-C1, REQ-B4.1
dedup key) rests on a field-presence assumption not confirmed by the project's own vendored
dependency documentation, and this reviewer could not independently confirm it live.

**Evidence (file:line)**:
`~/.anicca/skills/earn/hl-trade/.venv/lib/python3.14/site-packages/hyperliquid/info.py:201-271`
(`user_fills`/`user_fills_by_time` docstrings, no `fee`/`tid` field listed).

**Recommendation**: have the hardening-phase live E2E step explicitly log/assert the raw shape
of one real fill object before building the rest of the pipeline on top of it.

## F-6 — NOTE (positive confirmation, no action needed)

Cross-checked against current code and found accurate: `hl.py:61` mainnet usage; `hl.py:128-148`
(`cmd_close`) capturing pre-close `unrealizedPnl` and reporting it as `closed_pnl_usd`;
`run.sh:213` hard-coded `cost_usdc:0` with no `external` key; per-instance checkout separation
(confirmed via `~/.anicca`, `~/.anicca-founder`, `~/.blockrun` each having their own
`skills/earn/hl-trade/`); EDGE-10's claim that wallet `0xb9dd3b...` is unfunded/zero-fill
(confirmed against live `earn-ledger.jsonl`, only `hl-observe`/`hl-cooldown` lines present).

## F-7 — NOTE

**Dimension**: spec_fidelity
**Target**: REQ-E3

REQ-E3's "UNCONDITIONALLY... on EVERY wake" is scoped more narrowly than its wording suggests:
`run.sh`'s pre-existing P1 `earn-guard.mjs` HALT check (line ~85) can already `exit 0` before any
`STRATEGY=hl` branch code — including the new reconcile call — ever runs. No money-safety impact
(a halted wallet simply delays reconciling; no data loss), but recommend rewording for clarity.

**Evidence (file:line)**: `skills/earn/run.sh:85-88` (P1 guard, unconditional exit before any
STRATEGY branch); `.vcsdd/features/hl-realized-pnl/specs/behavioral-spec.md:195-199` (REQ-E3 wording).

## F-8 — NOTE

**Dimension**: spec_fidelity
**Target**: verification-architecture.md's `already_recorded_tids`

No NFR addresses the cost of scanning the entire (append-only, never-pruned per REQ-E2)
`earn-ledger.jsonl` every wake to build the tid dedup set. Not a money-safety issue at current
scale; forward-looking note only.

---

## Summary of severities

| ID | Severity | Dimension(s) |
|---|---|---|
| F-1 | BLOCKING | spec_fidelity, verification_readiness |
| F-2 | major | spec_fidelity |
| F-3 | major | spec_fidelity |
| F-4 | minor | spec_fidelity |
| F-5 | minor | spec_fidelity |
| F-6 | note | (confirmation) |
| F-7 | note | spec_fidelity |
| F-8 | note | spec_fidelity |

Blocking: 1. Major: 2. Minor: 2.
