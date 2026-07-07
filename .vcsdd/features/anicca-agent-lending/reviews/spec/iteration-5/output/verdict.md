# Spec Review Verdict — anicca-agent-lending — Iteration 5

**Overall verdict: FAIL**

## Part 1 — Re-verification of the 5 prior findings (FIND-301..305)

All five findings from iteration 4 are **genuinely resolved** on their technical merits. This is a
materially different outcome than iterations 1-4 (26 cumulative findings, no clean re-verification
pass until now). Detail:

| Finding | Status | Basis |
|---|---|---|
| FIND-301 (third terminal state / reconciliation-itself-throws) | **Resolved** | Cross-checked real source: `ledger.js:20-24` (`appendChild` is unguarded `fs.appendFileSync`, confirmed can throw) and `lock.mjs:187-209` (`withGigLock`'s `finally` releases the lock on ANY exception regardless of cause). The spec now grounds the reconciliation trigger purely on ledger STATE (an unterminated `provisioning`/`disbursement_uncertain` row), uniformly covering crash, in-process exception, and the follow-up-append-itself-throws case, plus the reconciliation-lookup-itself-throws case (PROP-106k/PROP-106l). |
| FIND-302 ("logged" ambiguity) | **Resolved** | Explicitly defined as strictly out-of-band, never a `loans.jsonl` append, backed by a Tier-0 structural check (PROP-108e). The replay-blocklist is also now scoped to "rows appended after a prior successful `verifyRepayment` call," closing the disbursement-vs-repayment-txHash ambiguity by append-source rather than an explicit schema field — sufficient for the security-relevant question. |
| FIND-303 (kill-switch wiring unverifiable) | **Resolved** | New Tier-0 `PROP-105h` demands a control-flow read of the REAL production issuance code (not `PROP-105g`'s mock), and Gate item (2) explicitly instructs the adversary that the mock is insufficient evidence. |
| FIND-304 (composition-point pipeline-shape gap) | **Resolved — and independently re-verified against `anicca-agent-spawn`'s ACTUAL current spec (not the frozen "iteration 6" citation)** | Freshly re-read the sibling spec this session: the real `filterProductiveCitizens → readCitizenBalances → computeColonySurplusUsd` three-step pipeline is confirmed unchanged even though the sibling has since moved to iteration 9 (unrelated findings, FIND-801/802, about Solana wallet-verification tooling and a `COORDINATOR_HOME` prose literal — neither touches the pipeline shape). This document's own fix explicitly names all three steps and places the composition correctly. |
| FIND-305 (`homeDir`/`coLocatedWithCoordinator` stale citation) | **Resolved — and independently re-verified** | Sibling's actual current seed data (`homeDir: "/Users/anicca/.anicca"` / `"/Users/anicca/.blockrun"`, both `coLocatedWithCoordinator: true`) matches exactly what this revision's Dependencies section now cites. REQ-112's mechanism reads `coLocatedWithCoordinator` exclusively, never `homeDir` equality. |

A structural note worth flagging (not itself a blocking finding, since the document's own design
explicitly anticipates and accepts this): the Dependencies/REQ-113 sections cite `anicca-agent-spawn`
as being at "iteration 6... FIND-501..504" — the sibling's real, current `state.json` shows **iteration
9**, gate FAIL, timestamp `2026-07-07T12:34:17.486Z`, findings **FIND-801/FIND-802** (a different area
entirely — wallet-identity verification tooling, not the registry shape this feature depends on). This
is exactly the moving-target behavior REQ-113 was written to make survivable, and it does survive it:
the *substantive* facts (pipeline shape, field shape, seed values) this feature's fixes depend on remain
accurate, even though the specific iteration number cited is (predictably, by design) already stale.

## Part 2 — Fresh, full pass over the rest of the spec

Three new, previously-unflagged findings emerged from a fresh line-by-line pass:

### FIND-401 (critical, spec_fidelity) — Borrower double-loan race across different lenders
REQ-102's own EARS text states a binding "at most one outstanding loan at a time" invariant. But
REQ-106's concurrency-safety mechanism is a **per-lender** lock (`loan_${lenderId}`) — REQ-106's own
Edge Cases explicitly celebrate cross-lender non-contention as "intentional, not a bug." Because
REQ-102's borrower-eligibility check is a plain, unlocked read performed independently by each lender's
own issuance flow, two *different* lenders can each observe the same borrower as eligible and both
disburse — no mechanism serializes this. Worse: since `"provisioning"`/`"disbursement_uncertain"` rows
don't count as an open obligation under REQ-102's condition (c), and reconciliation for a given lender
only fires "at the START of the NEXT loan-issuance attempt for THAT SAME lender" (which may never
happen soon), this is not a millisecond-scale race but a window that can persist indefinitely. This is
the exact same lock-scope-narrower-than-invariant-scope hazard class this spec has already spent three
iterations (FIND-103/FIND-201/FIND-301) hardening for the *lender* side — the *borrower*-side analog is
never once discussed. No proof obligation (`PROP-102c`, `PROP-106e`) tests this.

### FIND-402 (critical, spec_fidelity) — No self-lending exclusion
Nothing in REQ-101/102/105/111 requires `lender_id !== borrower_id`. A self-funded citizen can
self-loan-and-self-repay at negligible real cost (REQ-104's smallest loan totals $0.022) to freely
inflate `successfulOnTimeRepayments`, defeating REQ-105's entire cold-start risk-mitigation rationale
(a fabricated track record backing a real loan from a genuine, separate lender) and silently corrupting
`computeColdStartRepaymentRate`'s own monitoring signal that the kill-switch depends on.

### FIND-403 (major, spec_fidelity) — `issued_ms` undefined relative to the two-phase issuance append
`issued_ms` drives REQ-109's default-detection clock and REQ-105's cold-start ordering but is never
defined relative to REQ-106's two distinct row timestamps (`provisioned_ms` on the provisional row vs.
the follow-up active row). This creates a real ambiguity specifically in the crash-recovery/
reconciliation-delay path this spec otherwise hardens so carefully — either silently shortening a
borrower's real repayment window, or giving reconciled loans an inconsistent, longer one.

## Conclusion

Do not treat this as a "mostly converged, minor cleanup" result. Three critical/major findings remain,
at least one of which (FIND-401) is a genuine money-safety concurrency gap in the SAME class this
feature has already required three rounds of hardening to close on the lender side — it was never
extended to the borrower side. `overallVerdict: FAIL`.
