# VCSDD Adversary Verdict — anicca-agent-lending, Phase 1c spec review, iteration 2

**Overall verdict: FAIL**

Fresh-context review (zero prior conversation access). All 8 iteration-1 findings were re-verified
against the REAL, current source files (not merely trusted from the spec's own resolution claims). 7
NEW findings were identified in this pass. See individual `findings/FIND-1NN.json` files for full
evidence and citations.

## Iteration-1 findings: re-verification results

| Finding | Status |
|---|---|
| FIND-001 (loan_id collision) | **Genuinely resolved.** Walked the concurrency scenario end-to-end: `nextLoanSequenceForLender` filters by the structured `lender_id` field first (safer than `child-spec.js`'s own prefix-string-only matching), and `n` is computed strictly inside the same per-lender lock. Cross-lender collision is structurally impossible. |
| FIND-002 (missing host-scoping) | **Genuinely resolved** on its own narrow terms (REQ-112 now exists and correctly extends to both lender and borrower). See FIND-101 below for a related, deeper problem with what REQ-112 assumes about the sibling spec. |
| FIND-003 (facilitator precondition) | **Genuinely resolved.** `escrow.mjs`/`gig.mjs` re-read fresh; the cited signature and `GIG_FACILITATOR_URL` resolution pattern are accurate. |
| FIND-004 ($0.02 overclaim) | **Genuinely resolved.** Sizing vs. economic claims are honestly separated. See FIND-107 for a gap in the monitoring function itself. |
| FIND-005 (gojo coordination) | **Resolution is incomplete — the fix itself introduces a new, more serious bug.** See FIND-102: the new `sumRecentGojoGiftsUsd` has no lender-scoping and, as literally specified, misattributes one specific citizen's gojo commitments to every lender. |
| FIND-006 (stale citizens.json citation) | **The narrow citation gap is fixed, but the underlying drift risk has recurred and gotten worse.** See FIND-101: the sibling spec is now at iteration 5, not iteration 4 as cited, with critical new findings bearing directly on REQ-112. |
| FIND-007 (false escrow.mjs claim) | **Genuinely resolved for the `to`-topic check.** `record-earn.mjs` re-read fresh; the citation is accurate for that half. See FIND-105 for an overclaim on the `from`-topic half. |
| FIND-008 (interest rate justification) | **Genuinely resolved.** Now honestly framed as a tunable starting parameter. |

## New findings (iteration 2)

| ID | Dimension | Severity | Summary |
|---|---|---|---|
| FIND-101 | spec_fidelity | critical | Dependencies section cites `anicca-agent-spawn` as "iteration 4"; the real spec is now iteration 5, with critical findings (a real remote-Akash spawn-child mechanism; dual-wallet aggregation gap) that directly threaten REQ-112's framing of "remote citizen" as a rare, deferred edge case rather than the likely dominant future case. |
| FIND-102 | spec_fidelity | critical | `sumRecentGojoGiftsUsd` has no `lenderId` parameter and REQ-101 never gates the subtraction by which lender is being evaluated — despite the spec's own prose acknowledging attribution only works for the one citizen whose `run.sh` writes the log. As specified, every OTHER lender's surplus is incorrectly reduced by that one citizen's own gifts. |
| FIND-103 | verification_readiness | critical | REQ-106 only handles `payViaFacilitator` FAILURE fail-closed. A crash AFTER a successful on-chain disbursement but BEFORE the `loans.jsonl` append is never addressed — the reclaiming caller recomputes the same sequence number and can re-disburse, producing a real, untracked double-payment. |
| FIND-104 | verification_readiness | major | REQ-106's lock discipline covers issuance only. REQ-108 (repayment) and REQ-109 (default detection) append to the same `loans.jsonl` with zero lock/mutual-exclusion discipline — an unaddressed race between a repayment landing and a default sweep for the same `loan_id`. |
| FIND-105 | verification_readiness | major | REQ-108 claims the `from`-topic check is "decoded the same way" as `record-earn.mjs`'s already-hardened `to`-topic check. In fact `record-earn.mjs` never equality-checks `from` at all (only set-membership) — the `from`-side exact-match REQ-108 requires has no real precedent in the cited file, despite the "already-hardened, reused" framing. |
| FIND-106 | spec_fidelity | major | REQ-102 says `BORROWER_LOW_USD` "reus[es] `decide.mjs`'s ... constant verbatim"; REQ-110's own Tier-0 acceptance criterion says lending and `decide.mjs` "share zero code coupling — neither imports the other." Both cannot be literally true. |
| FIND-107 | spec_fidelity | major | `computeColdStartRepaymentRate`'s definition of a "cold-start loan" ("every borrower's own first-ever loan") contradicts REQ-105's own edge case (a late repayment never increments the on-time count, so a borrower can have multiple `successfulOnTimeRepayments=0` loans) — and the function's own operational algorithm for identifying such loans from raw rows is never specified. |

## Dimension verdicts

- **spec_fidelity: FAIL** (FIND-101, FIND-102, FIND-106, FIND-107)
- **verification_readiness: FAIL** (FIND-103, FIND-104, FIND-105)

## Positive evidence (what was checked and holds)

- `lock.mjs`, `ledger.js`, `escrow.mjs`, `child-spec.js`, `is-self-funded.mjs`, `decide.mjs` were all
  read fresh this session; every literal signature/constant citation in the spec against these six files
  is accurate (facilitatorUrl-no-default, `DEFAULT_LOW_USDC=0.5`, `DEFAULT_RESERVE_USDC=5.0`,
  `isSelfFunded`'s `{wallet,fuel,humanDependencies}` contract, `nextChildId`'s algorithm).
- `ubi.js`/`run.sh`/the real `gojo-log.jsonl` row were read fresh; the file path and row shape citation
  in the Dependencies section is accurate (though see FIND-102 for the resulting attribution bug).
- The `loan_id` collision-freedom design (FIND-001's resolution) was independently walked through step
  by step against the real `lock.mjs` semantics and found sound.

This project's own sibling feature, `anicca-agent-spawn`, needed 5+ Phase-1c iterations (and counting)
to converge, with critical findings still surfacing at iteration 5. Given the volume and severity of
new findings in this second pass of a much smaller spec, convergence should not be assumed to be near.
