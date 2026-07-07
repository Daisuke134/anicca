---
status: approved
feature: anicca-agent-lending
sprintNumber: 1
negotiationRound: 1
scope: Pure-core eligibility/sizing/monitoring layer (REQ-101/102/104/105/109/114), REQ-107's chain/asset scope gate, REQ-106's pure per-lender sequencing/lock-order helpers, REQ-108's independent on-chain repayment verification, and REQ-106's crash/uncertain-disbursement on-chain reconciliation lookup. Files touched (all in ~/anicca, repo github.com/Daisuke134/anicca, branch main) — see the body's Scope section for the full file list. This sprint does NOT include the effectful issuance/repayment ORCHESTRATOR; see the body's Known residual scope boundary section.
criteria:
  - id: CRIT-001
    dimension: spec_fidelity
    description: Every function exported from lending-gate.mjs is pure — zero I/O (no fs, no fetch/network, no Date.now()-based nondeterminism beyond parameters explicitly passed in) — matching the Purity Boundary Map's classification of this module as "Pure Core" for REQ-101/102/104/105/106 (pure helpers only)/109/114 (verification-architecture.md lines 14-30).
    weight: 0.15
    passThreshold: A control-flow read of ~/anicca/skills/economy/lending/lib/lending-gate.mjs confirms its only import is isSelfFunded from ../../../_shared/lib/is-self-funded.mjs (itself pure), and no function body anywhere in the file references fs, fetch, require("http"), readFileSync, or any network/filesystem global. Every nowMs figure a function needs (computeRecentDefaultLossUsd, sumRecentGojoGiftsUsd, detectDefaultedLoans) is an explicit parameter, never an internal Date.now() call. FAIL if any I/O call or internal wall-clock read is found anywhere in this file.
  - id: CRIT-002
    dimension: verification_readiness
    description: The full target-feature test suite (skills/economy/lending/lib/__tests__/*.test.mjs) is genuinely green, independently re-run by the Phase 3 adversary itself — not accepted from the builder's own log.
    weight: 0.15
    passThreshold: Adversary runs cd ~/anicca && node --test skills/economy/lending/lib/__tests__/*.test.mjs itself and confirms the process exits 0 with exactly 75/75 passing (0 fail, 0 cancelled), matching evidence/sprint-1-green-phase.log's own recorded count. FAIL if the count differs from 75/75, if any test is skipped/todo, or if the adversary does not actually execute the command itself.
  - id: CRIT-003
    dimension: spec_fidelity
    description: isBorrowerEligible checks condition (d) self-loan exclusion FIRST, then REQ-107's wallet.evm chain-scope gate, then (a) self-funded, (b) below BORROWER_LOW_USD, (c) zero open obligation — and its six possible reason values ("self_loan", "not_evm", "not_self_funded", "not_broke_enough", "outstanding_loan", "ok") never collide with one another (REQ-102/REQ-107, PROP-102e/PROP-107a).
    weight: 0.15
    passThreshold: A control-flow read of isBorrowerEligible in lending-gate.mjs confirms the lenderId===borrowerId check is the first statement in the function body (returning reason:"self_loan"), the wallet.evm!==true check is the second (returning reason:"not_evm"), and the six literal reason strings used across the function are pairwise distinct. PLUS an independent re-run of node --test skills/economy/lending/lib/__tests__/lending-gate.test.mjs confirms PROP-102e's own named test ("a self-loan candidate (lenderId===borrowerId) is rejected FIRST") and PROP-107a's own named test ("a Solana-only borrower (no wallet.evm) is excluded from borrower eligibility") both pass. FAIL if either check is reordered, if any reason string is reused for two different outcomes, or if either named test fails/is missing.
  - id: CRIT-004
    dimension: edge_case_coverage
    description: evaluateColdStartKillSwitch and evaluateOverallDefaultKillSwitch are independent, ADDITIVE gates (either alone refuses issuance), and evaluateOverallDefaultKillSwitch's absolute-loss branch uses >= (not >) against RECENT_DEFAULT_LOSS_THRESHOLD_USD, so a single bust-out default landing EXACTLY at REQ-105's own $5.00 loan ceiling trips it by itself (resolves this feature's own spec-review iteration-8 FIND-701).
    weight: 0.1
    passThreshold: Adversary re-runs lending-gate.test.mjs and confirms PROP-114d's own named test ("evaluateColdStartKillSwitch=false but evaluateOverallDefaultKillSwitch=true for the SAME request still refuses issuance") and PROP-114f's own named test ("volume-dilution-defeat proof") both pass; reads evaluateOverallDefaultKillSwitch's source and confirms the absolute-loss branch's comparison operator is literally >=, never >. FAIL if either named test fails, or if the comparison is found to be strict >.
  - id: CRIT-005
    dimension: spec_fidelity
    description: verifyRepayment rejects a txHash already credited anywhere in loans.jsonl — BOTH a same-loan replay and a cross-loan replay — checked BEFORE any value is credited, and independently re-verifies a claimed repayment against a finalized on-chain block via an exact, zero-padded-address Transfer-log match on BOTH the from and to topics (never a suffix/substring match on either side) (REQ-108, PROP-108a/b/e).
    weight: 0.15
    passThreshold: Adversary re-runs lending-verify.test.mjs and confirms, by name, the same-loan-replay test (PROP-108e), the cross-loan-replay test (PROP-108e), the to-topic-suffix-only-rejection test (PROP-108b/FIND-704), the from-topic-suffix-only-rejection test (PROP-108b/FIND-105), and the un-finalized-block-rejection test (PROP-108a) all pass. Reads verifyRepayment's source and confirms the alreadyCredited check runs before any RPC call, and matchesTransferLog checks topics[1] (from) and topics[2] (to) both via strict string equality against zero-padded addresses. FAIL if any named test fails, or if either topic check is found to use .includes/.endsWith instead of exact equality.
  - id: CRIT-006
    dimension: edge_case_coverage
    description: reconcileProvisionalDisbursement only ever READS on-chain state — it never itself invokes any transfer/settle/broadcast call — and correctly reports found:false when no matching log exists in the scanned block range (REQ-106, resolves FIND-103/FIND-201).
    weight: 0.1
    passThreshold: Adversary re-runs lending-verify.test.mjs and confirms the test named "reconcileProvisionalDisbursement only ever READS on-chain state — never invokes any transfer/settle call itself" passes (asserting a spied eth_sendRawTransaction handler is never invoked), AND the "reports no match when the on-chain lookup finds nothing" test passes. Reads reconcileProvisionalDisbursement's source and confirms it calls only eth_getLogs (a read method), never any write/broadcast RPC method. FAIL if either named test fails or if any write-RPC method call is found in this function's body.
  - id: CRIT-007
    dimension: spec_fidelity
    description: nextLoanSequenceForLender is namespaced per-lender (two different lenders' own sequences never collide) and treats "provisioning"/"disbursement_failed"/"active"/"disbursement_uncertain" rows for the SAME loan_id as one already-claimed sequence number; resolveLoanLockAcquisitionOrder deterministically returns [lexicographically-smaller key, other key] for both possible input orderings (REQ-106, PROP-106e/PROP-106m).
    weight: 0.1
    passThreshold: Adversary re-runs lending-gate.test.mjs and confirms the PROP-106e per-lender-namespacing test, the PROP-106e/g/h/k unterminated-row test, and the PROP-106m both-orderings test all pass by name. FAIL if any of these three named tests fails.
  - id: CRIT-008
    dimension: spec_fidelity
    description: REQ-110's zero-coupling requirement holds — this feature's own independently-declared constants (BORROWER_LOW_USD, GOJO_SENDER_ID) are never imported from, and never imported by, economy/gig/decide.mjs or economy/ubi/run.sh — a same-numeral definitional match, never a code coupling.
    weight: 0.05
    passThreshold: A structural grep across skills/economy/lending/lib/*.mjs for any import of DEFAULT_LOW_USDC or any other named export from decide.mjs/run.sh finds zero hits, AND a grep of decide.mjs/run.sh for BORROWER_LOW_USD or GOJO_SENDER_ID finds zero hits. FAIL if either grep finds a hit.
  - id: CRIT-009
    dimension: verification_readiness
    description: The purity-boundary discipline holds across this sprint's four modules as a set — lending-gate.mjs is the sole pure-core module (zero I/O, CRIT-001); lending-path.mjs exports only a computed constant (zero runtime logic beyond path.join); gojo-read.mjs and lending-verify.mjs are the ONLY two modules in this sprint's diff that touch fs/network, and each does so for exactly one narrowly-scoped purpose (gojo-read.mjs — read-only fs.readFileSync over gojo-log.jsonl; lending-verify.mjs — JSON-RPC fetch calls only).
    weight: 0.05
    passThreshold: Adversary reads all four library files and confirms — lending-path.mjs contains no function exports, only the LOANS_LEDGER_PATH constant; gojo-read.mjs's only side-effecting call is fs.readFileSync (no fs.writeFileSync/fs.appendFileSync anywhere in the file); every network call in lending-verify.mjs goes through the single local rpcCall helper (no direct inline fetch elsewhere in the file). FAIL if any of these boundaries is violated.
---

## Scope

This sprint delivers exactly the pure-core eligibility/sizing/monitoring layer plus the two effectful,
narrowly-scoped modules needed to independently re-verify on-chain repayment and reconcile a
crashed/uncertain disbursement — REQ-101, REQ-102, REQ-104, REQ-105, REQ-107, REQ-109, REQ-114 (fully,
as pure functions), REQ-106 (its pure per-lender sequencing/lock-ordering helpers plus its crash/
in-process-exception reconciliation lookup — NOT its live issuance orchestration), and REQ-108 (its
independent on-chain repayment verification — NOT its live repayment-orchestration lock race). REQ-103/
REQ-110/REQ-111 (design constraints: no LLM/scoring logic, zero coupling with `decide.mjs`, reuse of
`isSelfFunded` unmodified) hold structurally across all four files in this diff, per CRIT-001/CRIT-008.

Files touched (all in `~/anicca`, repo `github.com/Daisuke134/anicca`, branch `main`):
- `skills/economy/lending/lib/lending-path.mjs` (new)
- `skills/economy/lending/lib/lending-gate.mjs` (new)
- `skills/economy/lending/lib/gojo-read.mjs` (new)
- `skills/economy/lending/lib/lending-verify.mjs` (new)
- `skills/economy/lending/lib/__tests__/lending-path.test.mjs` (new)
- `skills/economy/lending/lib/__tests__/lending-gate.test.mjs` (new)
- `skills/economy/lending/lib/__tests__/gojo-read.test.mjs` (new)
- `skills/economy/lending/lib/__tests__/lending-verify.test.mjs` (new)

Phase 2b/2c evidence on file: `evidence/sprint-1-green-phase.log` (target-feature-tests: PASS,
regression-baseline: PASS — 75/75 in `skills/economy/lending/lib/__tests__`). Phase 2c refactor: two
clarifying-comment tightenings in `lending-gate.mjs` (`isBorrowerEligible`'s six-value `reason` enum
made explicit) and `lending-verify.mjs` (`extractTxHash`'s malformed-RPC-response fallback rationale
made explicit) — zero behavior change, re-verified 75/75 green after each edit. No code duplication was
found across the four modules requiring extraction; each module's responsibility (pure gate logic vs.
path constant vs. read-only gojo-log reader vs. on-chain verification) was already cleanly separated at
Green-phase.

## Known residual scope boundary

This sprint's four modules do NOT include the effectful loan-issuance/repayment ORCHESTRATOR — the
code that would acquire `lock.mjs`'s nested per-lender/per-borrower `withGigLock` pair (via
`resolveLoanLockAcquisitionOrder`), append `ledger.js`'s provisional/follow-up `loans.jsonl` rows via
`LOANS_LEDGER_PATH`, invoke `escrow.mjs`'s `payViaFacilitator` for the actual USDC transfer, and invoke
`reconcileProvisionalDisbursement`/`verifyRepayment` as part of that live flow. No such orchestrator
file exists anywhere in this diff as of this sprint. Consequently, the Tier-2/3 proof obligations
that depend on that orchestration actually existing and running — PROP-106a/b/n (concurrent
issuance / cross-lender double-borrow race), PROP-106e's Tier-2 half (concurrent real disbursement
calls against two distinct lenders, distinct from its already-satisfiable Tier-1 per-lender-namespacing
half), PROP-106f (fail-closed disbursement-failure handling, requires the real orchestrator call site
to inject a mocked `payViaFacilitator` into), PROP-106g/h/k/l wired into a live issuance attempt
(today they are exercised directly against `reconcileProvisionalDisbursement` in isolation, not via a
real issuance call site), PROP-106o (`issued_ms`/`due_ms` computed from the real active-row append
timing), PROP-106p (fresh lock-protected kill-switch re-check), PROP-108c/d
(partial-repayment transition and the repayment-vs-default-sweep lock race), and PROP-112a's
runtime co-location check — are NOT satisfied by this sprint and MUST NOT be scored as delivered
against this contract. This is a scope boundary, not a hidden defect: this sprint's own stated scope
(see the Scope section above) is the pure-core/verification/reconciliation layer only. Building the
orchestrator against these four modules, and closing the listed proof obligations, is tracked as a
separate, future sprint.

**Completeness correction (2026-07-08, Phase 5 formal hardening)**: PROP-106e's Tier-2 half, PROP-106f,
and PROP-106o were found during Phase 5 to share this identical root cause but were omitted from the
original enumeration above — added here for completeness. No scope change: these three obligations
were always structurally out of reach without the orchestrator: this is a documentation-accuracy fix,
not a new scope decision.

**Second completeness correction (2026-07-08, Phase-6 gate check)**: five additional Tier-0 structural
obligations were found, when attempting to enter Phase 6, to ALSO require the real, production
issuance-critical-section code to exist before they can be checked, and were never previously named as
in-scope OR out-of-scope anywhere: PROP-109e (the defaulted-append call site acquiring `loan_${loan_id}`
before writing), PROP-106i (REQ-106's own issuance critical section never referencing the per-loan lock
key), PROP-105h/PROP-114c (the real issuance module's own call sites for both kill-switches, including
their required second, lock-protected re-check call sites), and PROP-109g (the real defaulted-append
call site setting `defaulted_ms`) — each explicitly requires reading "the REAL, PRODUCTION
issuance-critical-section code," which does not exist yet. A sixth, PROP-112a, was found to be only
HALF checkable without the orchestrator: its structural grep half (no `homeDir`-equality comparison, no
remote/networked lock construction) was independently verified against the delivered code and holds,
but its own required "unit-test fixture asserting co-location eligibility via `coLocatedWithCoordinator`"
needs an actual co-location-decision function that also does not exist in any of this sprint's four
delivered modules — so it is deferred in full, not partially credited. All six are added to sprint-2's
scope alongside the thirteen above (nineteen total proof obligations deferred, all sharing the identical
root cause: no loan-issuance/repayment orchestrator exists yet in this sprint's diff).

## Formatting note (2026-07-08)

This contract was originally drafted with YAML `>` folded block-scalar syntax for the `description`/
`passThreshold` fields, `sprint`/`date` frontmatter keys, and a `knownResidualFindings` frontmatter
array. `vcsdd-state.js`'s `parseStructuredFrontmatter` is a minimal custom parser (not a full YAML
library) that does not support folded block scalars and enforces the exact schema in
`vcsdd-contract.schema.json` (`sprintNumber` not `sprint`, no `date`, no `knownResidualFindings` at the
top level). The frontmatter was reformatted to single-line field values and the disallowed keys were
removed (their content preserved verbatim in this document's body, which already carried it) — this is
a structural/parser-compatibility fix only; no criterion's substantive content changed. Because this
changed the contract's digest, it required a fresh contract review (`reviews/contracts/sprint-1/`,
round 2) rather than reusing round 1's PASS verdict.
