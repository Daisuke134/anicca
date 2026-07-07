# VCSDD Adversary Verdict — anicca-agent-lending — Phase 1c Spec Review — Iteration 1

**Overall Verdict: FAIL**

Reviewed fresh-context, disk-only: `specs/behavioral-spec.md` (REQ-101..111), `specs/verification-architecture.md`
(PROP-101a..111b), and cross-checked every cited source file (`ledger.js`, `lock.mjs`, `is-self-funded.mjs`,
`decide.mjs`, `escrow.mjs`, `gig.mjs`, `ubi/run.sh`, `ubi.js`, `child-spec.js`, `record-earn.mjs`,
`anicca-agent-economy/SPEC.md` §9.9, `anicca-agent-spawn/behavioral-spec.md`) directly, not from the spec's
own description of them.

## Dimension verdicts

| Dimension | Verdict | Findings |
|---|---|---|
| spec_fidelity | **FAIL** | FIND-001, FIND-003, FIND-004, FIND-005, FIND-006, FIND-008 |
| verification_readiness | **FAIL** | FIND-002, FIND-007 |

## Findings summary

| ID | Severity | Category | Summary |
|---|---|---|---|
| FIND-001 | critical | spec_gap | `loan_id` generation is never specified anywhere, yet every REQ (101/102/104/105/108/109) depends on a "last-write-wins per `loan_id`" reduction. REQ-106 explicitly permits unlocked concurrent issuance across *different* lenders. If ID assignment follows the only existing colony precedent (`child-spec.js::nextChildId`, itself lock-free), two unrelated loans issued concurrently by two different lenders can collide on the same `loan_id`, silently merging their bookkeeping. |
| FIND-002 | critical | purity_boundary | Reuses `lock.mjs`/`ledger.js` (local-filesystem primitives) for a two-party (lender + borrower, generally different citizens) mechanism without the "single coordinator host" scope-narrowing constraint that `anicca-agent-spawn`'s own REQ-106 states is the *precondition* for that same reuse to be correct. Never specifies which process/host executes disbursement (needs the lender's own private key), nor whether all lending participants are assumed co-located on one filesystem. |
| FIND-003 | major | security_surface | Dependencies section describes `payViaFacilitator({privateKey, to, amountBase})` but the real signature requires a mandatory `facilitatorUrl` (no default) pointing at a running x402-rs facilitator service. Neither the parameter nor the running-service precondition is mentioned anywhere in the spec. |
| FIND-004 | major | requirement_mismatch | `FIRST_LOAN_USD=0.02`'s justification cites SPEC.md §9.9's P2 WITNESS, but that $0.02 was a human-funded genesis injection to the *poster*, received by the *taker* — not evidence that $0.02 gives a *borrower* (receiving the loan) any realistic path to earn back $0.022 within 14 days. PROP-105a's claim to "resolve" the arXiv cold-start gap is unsupported on the repayment side. |
| FIND-005 | major | spec_gap | No discussion anywhere of interaction with the already-existing, already-witnessed `economy/ubi::distributeAI` (gojo) mutual-aid mechanism, which computes overlapping "surplus above reserve" arithmetic from the same balance with zero cross-awareness of `loans.jsonl` — real double-commit risk on the same lender's surplus. |
| FIND-006 | medium | spec_gap | Cited `citizens.json` shape is already stale vs. the current (iteration-4) `anicca-agent-spawn` spec, which added a `homeDir` field this citation omits — concrete, present-tense proof of the exact "sibling spec still evolving" risk both specs disclose only in the abstract. |
| FIND-007 | major | security_surface | REQ-108's `verifyRepayment` claims to reuse "escrow.mjs's own already-imported viem/createPublicClient dependency," but escrow.mjs contains no Transfer-log parsing at all. The colony's actual precedent (`record-earn.mjs`) has an already-fixed bug class (`FIND-704`: exact padded-topic equality, not a suffix match) that this spec neither cites nor requires reuse of — real risk of re-deriving a previously-fixed bug. |
| FIND-008 | minor | spec_gap | `LOAN_INTEREST_RATE=0.10`'s justification (reused from `ubi.js`'s unrelated profit-tithe `contributePct`) is a numeric coincidence, not a risk-based rationale for pricing an uncollateralized loan. |

## What was independently verified as accurate (not merely asserted by the spec)

- `citizens.json` is genuinely absent on disk (`~/anicca/skills/self/spawn/registry/` does not exist) — confirmed via filesystem glob.
- `ledger.js::readChildren`/`appendChild` are genuinely generic, file-path-parameterized, domain-agnostic — confirmed by reading the full 27-line file.
- `lock.mjs::withGigLock`/`isLockStale`'s real signature, atomic `fs.rename` reclaim, and `isSafeLockKey` character-set constraint match the spec's description exactly.
- `is-self-funded.mjs::isSelfFunded`/`selfFundedReasons` fail-closed behavior matches the spec's description exactly.
- `decide.mjs`'s `DEFAULT_LOW_USDC=0.5` and strict `<` boundary convention match REQ-102's citation exactly.
- The ladder arithmetic (`0.02`, `0.04`, `2.56`, capped `5.00` at n=8) is numerically correct.
- `total_due_usd = 0.02 * 1.10 = 0.022` is numerically correct.
- REQ-401/REQ-402/REQ-403 citations from `anicca-agent-spawn` genuinely exist with the claimed content (independent on-chain re-verification, retroactive-correction precedent).
- Franklin's Solana wallet address and claude-p's human-funded wallet address cited in REQ-107/REQ-111 match the project's own canonical records.

## Required for next iteration

All 8 findings must be resolved with specific, cited design decisions (not "will fix later"), per this
project's own established changelog discipline (see `anicca-agent-spawn/specs/behavioral-spec.md`'s own
iteration changelogs for the expected format). FIND-001 and FIND-002 are structural/critical and must be
resolved before the remaining findings can be meaningfully re-reviewed, since several other requirements
(REQ-101/102/105/108/109's correctness proofs) implicitly assume both are already solved.
