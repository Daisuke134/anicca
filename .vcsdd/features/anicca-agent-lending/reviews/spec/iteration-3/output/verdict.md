# Adversary Verdict — anicca-agent-lending, spec review iteration 3

**Overall verdict: FAIL**

Fresh-context review (zero prior conversation context). All 7 iteration-2 findings were
re-verified against the real, current spec text and real source files; the 3 architect-added
items were checked for internal consistency. 4 of 7 prior findings are genuinely resolved
without qualification (FIND-102, FIND-105, FIND-106, FIND-107). 2 are resolved for their literal
substance but a NEW defect was introduced by the fix itself or by a mislabeled cross-reference
(FIND-103 -> FIND-201; FIND-104 -> FIND-205). 1 architect-added item (the kill-switch threshold)
is internally self-contradictory and untested. 6 new findings (FIND-201..206) are filed.

## Prior findings (iteration 2) — re-verification results

| Finding | Status |
|---|---|
| FIND-101 (anicca-agent-spawn staleness) | **Genuinely resolved.** Re-checked the real, current `anicca-agent-spawn/state.json`: `gates.1c` shows iteration 6, FAIL, FIND-501..504, timestamped exactly as lending's own Dependencies section states. On-disk review folders confirm iteration 6 is the real latest (no iteration 7 exists yet). REQ-113's "re-verify at first use" discipline is sound. |
| FIND-102 (gojo lenderId gating) | **Genuinely resolved.** `sumRecentGojoGiftsUsd` is gated to `GOJO_SENDER_ID` throughout; confirmed against real `run.sh`. |
| FIND-103 (crash-safe two-phase issuance) | **Incomplete.** Closes the process-crash/stale-lock scenario, but a distinct in-process-exception scenario (settle succeeds, `waitForTransactionReceipt` throws) is never routed through `reconcileProvisionalDisbursement` at all. New critical finding: **FIND-201**. |
| FIND-104 (per-loan lock for repayment/default) | **Substance resolved, but a new labeling contradiction was introduced.** REQ-106's own Acceptance Criteria mislabels its own issuance-time append as "REQ-108/109 ledger append," contradicting REQ-108's explicit "DELIBERATELY DIFFERENT" lock-key framing. New finding: **FIND-205**. |
| FIND-105 (from-topic honest extension) | **Genuinely resolved.** Confirmed against real `record-earn.mjs`. |
| FIND-106 (REQ-102/REQ-110 coupling contradiction) | **Genuinely resolved.** |
| FIND-107 (cold-start recurrence false equivalence) | **Genuinely resolved.** |

## Architect-added items

| Item | Status |
|---|---|
| Kill-switch threshold (0.80 @ sampleSize>=10) | **Self-contradictory and untested.** Directly contradicts REQ-105's own adjacent, un-updated Edge Cases bullet ("this spec does not attach a decision rule ... to it this increment"). Zero backing proof obligation anywhere in verification-architecture.md's 43 PROPs. See **FIND-203**. |
| REQ-112 multi-host future-work note | Internally consistent, honestly scoped as researched-not-built. No finding. |
| REQ-109 gojo/UBI default-exclusion clarification | Consistent in isolation (confirmed gojo's targeting is structurally disconnected from `anicca-agent-spawn`'s registry). But the `excludeDefaultedBorrowers` mechanism it references has a separate, disproportionate cross-feature side effect. See **FIND-204**. |

## New findings (this iteration)

- **FIND-201 (critical, verification_readiness)** — The FIND-103 fix does not close a distinct
  double-disbursement path: an in-process exception from `payViaFacilitator` after `/settle`
  already succeeded is never routed through `reconcileProvisionalDisbursement`, because the lock
  gets released cleanly (not stale) on any thrown exception.
- **FIND-202 (critical, verification_readiness)** — REQ-108's repayment verification never
  de-duplicates by transaction hash; the same finalized transfer can be credited repeatedly
  toward one loan or replayed across different loans.
- **FIND-203 (critical, spec_fidelity)** — The kill-switch threshold directly contradicts an
  adjacent Edge Case in the same requirement and has zero proof-obligation backing.
- **FIND-204 (major, spec_fidelity)** — `excludeDefaultedBorrowers`'s composition into
  `anicca-agent-spawn`'s surplus pipeline zeroes a defaulted borrower's ENTIRE balance out of
  colony-wide spawn eligibility, disproportionate to the (possibly $0.02) defaulted debt, with no
  cap or write-off path, and this cross-feature consequence is never stated or reconciled.
- **FIND-205 (major, spec_fidelity)** — REQ-106's Acceptance Criteria mislabels its own
  issuance-time ledger append as "REQ-108/109 ledger append," contradicting REQ-108's own
  "DELIBERATELY DIFFERENT" lock-key claim.
- **FIND-206 (major, verification_readiness)** — Every dollar-arithmetic pure function in this
  feature omits this codebase's own established `.toFixed(6)` money-precision convention (present
  in `ubi.js`/`decide.mjs`), while demanding exact-equality acceptance criteria against unclamped
  floating-point results.

## Dimension verdicts

| Dimension | Verdict | Findings |
|---|---|---|
| spec_fidelity | **FAIL** | FIND-203, FIND-204, FIND-205 |
| verification_readiness | **FAIL** | FIND-201, FIND-202, FIND-206 |
