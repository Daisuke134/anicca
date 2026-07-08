---
status: approved
feature: anicca-agent-lending
sprintNumber: 2
negotiationRound: 1
scope: The effectful lending ORCHESTRATOR layer — the code that actually wires sprint-1's pure/narrow modules (lending-gate.mjs, lending-verify.mjs, gojo-read.mjs, lending-path.mjs) plus the two already-hardened, reused effectful modules (lock.mjs, escrow.mjs::payViaFacilitator) into two real, runnable flows. This sprint delivers REQ-115 (new, the loan-issuance orchestrator, executeLoanIssuanceAttempt) and REQ-116 (new, the loan-servicing orchestrator pair, executeRepaymentClaim + executeDefaultDetectionSweep) in a NEW module skills/economy/lending/lib/lending-orchestrator.mjs. REQ-101 through REQ-114 do NOT get new behavioral content this sprint beyond REQ-115/REQ-116 — they were already fully specified, EARS-clause-through-acceptance-criteria, across sprint-1's own 9 Phase-1c spec-review iterations (see the Pre-existing spec confirmation section below for the citation-by-citation proof of this claim). This sprint's own Phase 1a/1b work is this contract plus REQ-115/PROP-115a-d and REQ-116/PROP-116a-e — not a rewrite of any REQ-101 through REQ-114.
criteria:
  - id: CRIT-201
    dimension: structural_integrity
    description: Exactly one function, executeLoanIssuanceAttempt, in exactly one new module (~/anicca/skills/economy/lending/lib/lending-orchestrator.mjs), calls REQ-101/102/104/105/106/112/114's own already-exported functions in the canonical 9-step order REQ-115 states — no second, competing issuance-orchestration entry point exists anywhere in the diff, and no incidental edits are made to any sprint-1-delivered file (lending-gate.mjs, lending-verify.mjs, gojo-read.mjs, lending-path.mjs all remain byte-identical to their sprint-1-delivered content except for import additions this sprint's own new module makes into them).
    weight: 0.15
    passThreshold: A control-flow read of lending-orchestrator.mjs confirms a single call-graph root reaching every one of REQ-101/102/104/105/106/112/114's own exported functions, in the canonical order REQ-115 states, and that no second module/function anywhere in the diff independently re-implements or re-sequences any subset of that call graph. FAIL if a second orchestration path exists for issuance, or if any sprint-1-delivered file's own exported function signatures or internal logic are modified.
  - id: CRIT-202
    dimension: structural_integrity
    description: Neither executeLoanIssuanceAttempt nor executeRepaymentClaim nor executeDefaultDetectionSweep contains decision/judgment logic of its own — no arithmetic/boolean eligibility, sizing, or default-detection comparison and no LLM/prompt reference anywhere in lending-orchestrator.mjs — mirroring REQ-103's own bookkeeping-only discipline, extended by REQ-115/REQ-116 to these three new functions exactly as anicca-agent-spawn REQ-307/PROP-307b extends REQ-104's identical discipline to its own orchestrator.
    weight: 0.1
    passThreshold: Structural grep of lending-orchestrator.mjs finds no relational/threshold comparison against a balance/surplus/rate/count value anywhere outside a call into an already-exported REQ-101/102/104/105/106/108/109/112/114 function, and no prompt/LLM-client reference. FAIL if either is found.
  - id: CRIT-203
    dimension: edge_case_coverage
    description: A failure or refusal injected at each of REQ-115's 9 canonical issuance steps in turn is recorded correctly against the REAL executeLoanIssuanceAttempt — steps 1/2/3 (self-loan, non-co-located party, a tripped pre-lock kill-switch) append zero rows and acquire zero locks; step 4 (lock_held) appends zero rows; step 5 (a reconciliation lookup that itself throws) appends zero rows and consumes zero sequence numbers; step 6 (the fresh lock-protected recheck refuses) appends zero rows; step 8 (the provisional appendChild call itself throws before ever committing) leaves zero rows for that attempt's own n; step 9's three sub-cases (clean disbursement failure, an in-process exception after settle succeeds, and the follow-up appendChild call itself throwing) each append the follow-up row exactly per REQ-106's own already-specified two-phase/reconciliation shape (disbursement_failed, disbursement_uncertain, or an unterminated provisioning row later reconciled) — no step anywhere ever produces a row claiming active for a loan that was not genuinely, verifiably disbursed.
    weight: 0.2
    passThreshold: An integration test triggering a failure/refusal at each of the 9 canonical steps in turn against the REAL executeLoanIssuanceAttempt (never a mocked stand-in) confirms the ledger effect, or non-effect, at each step exactly matches the already-specified REQ-101/102/105/106/112/114 edge case for that step. FAIL if any step's failure produces an unexpected row, a wrongly-shaped row, a row claiming active without genuine disbursement, or if any step's own zero-row guarantee is violated.
  - id: CRIT-204
    dimension: structural_integrity
    description: The loan_lenderId and loan_borrower_borrowerId locks (REQ-106) are held together, via the REAL executeLoanIssuanceAttempt, from before step 5 begins until after step 9 completes or a refusal/failure at step 5, 6, 8, or 9 is resolved — never released any earlier — and the loan_loanId lock (REQ-108/109) is, via the REAL executeRepaymentClaim/executeDefaultDetectionSweep, held across each function's own entire read-verify-append critical section and is never acquired, referenced, or nested inside REQ-106's own per-lender/per-borrower critical section, and vice versa.
    weight: 0.15
    passThreshold: An integration test reusing PROP-106a's/PROP-106n's own staggered-race proof method, invoking the REAL executeLoanIssuanceAttempt (with steps unrelated to the lock itself stubbed to fast, real-shaped fixture I/O) rather than a bare fixture fn stand-in, confirms the dual-lock's real combined scope matches REQ-106's own already-specified critical section. A structural/Tier-0 read of lending-orchestrator.mjs confirms executeRepaymentClaim/executeDefaultDetectionSweep reference only loan_loanId as their lock key, never loan_lenderId or loan_borrower_borrowerId, and executeLoanIssuanceAttempt references only the two per-lender/per-borrower keys, never loan_loanId. FAIL if either lock's real scope diverges from its own already-specified critical section, or if either orchestrator function references the other's lock key.
  - id: CRIT-205
    dimension: verification_readiness
    description: (Revised, contract-review round 1, resolves FIND-C201 — re-scoped to be genuinely evaluable AT THIS gate, before Phase 3/5 run; final promotion of the 19 obligations remains independently enforced by vcsdd-harden's own standard "all required obligations proved" gate before Phase 6, this criterion does not weaken that — mirrors the identical fix anicca-agent-spawn sprint-2's own CRIT-205 already applied for the same reason.) Every one of the 19 obligations contracts/sprint-1.md's own Known residual scope boundary section deferred (PROP-106a, PROP-106b, PROP-106n, PROP-106e's Tier-2 half, PROP-106f, PROP-106g, PROP-106h, PROP-106k, PROP-106l, PROP-106o, PROP-106p, PROP-108c, PROP-108d, PROP-112a, PROP-109e, PROP-106i, PROP-105h, PROP-114c, PROP-109g) has a genuinely exercisable proof path in the CURRENT implementation — the real function/call site each obligation's own verification method names actually exists in lending-orchestrator.mjs as written, so nothing in the current code makes any of the 19 structurally unprovable.
    weight: 0.2
    passThreshold: For each of the 19 listed PROP IDs, a read of its own verification method (in verification-architecture.md) against the current lending-orchestrator.mjs source confirms the named call site/function genuinely exists and is reachable. FAIL if any of the 19 names a call site that does not exist in the current implementation, is unreachable, or is a stub/placeholder — NOT if a PROP is simply not yet promoted to status:proved in state.json (that promotion is Phase 3/5's own job, independently gated by vcsdd-harden before Phase 6).
  - id: CRIT-206
    dimension: implementation_correctness
    description: PROP-108a (REQ-108's own pre-existing Tier-3 live-E2E obligation — a real disbursement transfer plus a real repayment transfer, independently re-verified via a separate RPC call, on at least one real Base-mainnet-class result) is NOT claimed proved via a fixture, a simulated transfer, or a borrowed/historical artifact from a different feature or a different chain — it requires either a genuinely NEW real USDC disbursement-then-repayment pair executed through this sprint's own REAL executeLoanIssuanceAttempt/executeRepaymentClaim functions, or an explicit, honest re-deferral to a dedicated future checkpoint, exactly mirroring anicca-agent-spawn sprint-2's own CRIT-206 treatment of its own Tier-3 obligations.
    weight: 0.1
    passThreshold: A read of whichever artifact/evidence file claims PROP-108a proved confirms a genuinely fresh, real on-chain disbursement transaction hash AND a genuinely fresh, real on-chain repayment transaction hash minted THIS sprint through the real orchestrator functions (never a citation of sprint-1's own fixture-only test runs, and never a borrowed artifact from anicca-agent-economy's or anicca-agent-spawn's own prior live witnesses) — OR the contract explicitly re-defers it, citing this section. FAIL if PROP-108a is claimed proved via a fixture, a simulated transfer, or a borrowed artifact.
  - id: CRIT-207
    dimension: verification_readiness
    description: This sprint's own Phase 1a/1b artifact (REQ-115/REQ-116 in behavioral-spec.md, PROP-115a-d/PROP-116a-e in verification-architecture.md, this contract) is reviewed by a fresh-context adversary (Phase 1c) BEFORE Phase 2 (TDD) begins, exactly as sprint-1's own REQ-101 through REQ-114 spec was reviewed before ITS Phase 2 began — this sprint is not exempted from Phase 1c merely because most of its underlying spec content pre-dates it.
    weight: 0.1
    passThreshold: state.json shows a 1b to 1c transition with a recorded PASS verdict for this sprint's own contract plus REQ-115/REQ-116 and PROP-115a-d/PROP-116a-e, produced by a fresh vcsdd-adversary instance with zero Builder context. FAIL if Phase 2 begins without this gate.
---

## Pre-existing spec confirmation (this sprint's own Phase 1a/1b finding)

Before any new requirement text was written, this sprint's spec-crystallization phase re-read
`specs/behavioral-spec.md` and `specs/verification-architecture.md` in full and confirmed: REQ-101 (line
356), REQ-102 (482), REQ-103 (561), REQ-104 (598), REQ-105 (650), REQ-114 (831), REQ-106 (1097), REQ-107
(1656), REQ-112 (1687), REQ-113 (1793), REQ-108 (1872), REQ-109 (2049), REQ-110 (2197), REQ-111 (2229)
already carry full EARS clauses, edge cases, and acceptance criteria — each already adversary-hardened
across sprint-1's own 9 Phase-1c spec-review iterations (FIND-001 through FIND-702, resolved iteration by
iteration per `specs/behavioral-spec.md`'s own changelog tables). None of these fourteen requirements
needed new or rewritten behavioral content this sprint. The gap this sweep found, exactly mirroring what
`anicca-agent-spawn` sprint-2's own equivalent sweep found: every individual pure/narrow function and
every individual effectful primitive already had its own pinned signature and its own fully-specified
edge cases, but no function anywhere was named as the thing that actually wires them together into a
real, runnable flow — the Purity Boundary Map's own row list had no row for either binding function.
Unlike spawn (a single linear attempt with one trigger), this feature's own residual gap splits into TWO
distinct orchestration concerns with two genuinely different triggers, confirmed by reading each of the
19 deferred obligations' own text in `contracts/sprint-1.md`'s "Known residual scope boundary" section
against the specific flow it belongs to (see the Design decision section below) — this sprint's own
Phase 1a/1b work is exactly these two additions (REQ-115/PROP-115a-d, REQ-116/PROP-116a-e), never a
rewrite or duplication of REQ-101 through REQ-114's own already-hardened text.

## Design decision: issuance and repayment/default are TWO separate orchestrator entry points, not one

**The one real design question this sprint had to resolve**, per the dispatching agent's own framing: is
loan issuance and loan repayment-verification one single orchestrator entry point, or two separate ones?
Grounded in what each of the 19 deferred obligations actually needs to be wired INTO (read individually,
by ID, in `verification-architecture.md`):

- **Issuance-blocked** (15 of 19): PROP-106a, PROP-106b, PROP-106n, PROP-106e's Tier-2 half, PROP-106f,
  PROP-106g, PROP-106h, PROP-106k, PROP-106l, PROP-106o, PROP-106p, PROP-106i, PROP-105h, PROP-114c, and
  PROP-112a all name REQ-106's own per-lender/per-borrower dual-lock issuance critical section, its
  two-phase provisional/follow-up ledger append, its pre-lock-then-lock-protected-fresh-recheck
  kill-switch discipline, or REQ-112's co-location gate as evaluated AT ISSUANCE TIME — none of them name
  REQ-108/109's own per-loan lock or an already-issued loan's own post-issuance lifecycle.
- **Servicing-blocked** (4 of 19): PROP-108c, PROP-108d, PROP-109e, and PROP-109g all name REQ-108's
  repayment-verification append or REQ-109's default-detection append, BOTH of which act on an
  ALREADY-ISSUED (`status:"active"`) loan under REQ-108's own separate `` `loan_${loan_id}` `` lock — a
  structurally different critical section from REQ-106's own, per REQ-106's own PROP-106i (the two locks'
  critical sections are structurally disjoint) and per REQ-108's own explicit statement that this lock
  governs ONLY "their own LATER, independent repayment-verification/default-detection status-transition
  appends on an ALREADY-ACTIVE loan... never acquired, nested, or otherwise involved during issuance
  itself."

This 15-vs-4 split is not incidental — it reflects REQ-106 (issuance) and REQ-108/109 (servicing) being
two DIFFERENT triggers over two DIFFERENT lock scopes, exactly as the dispatching agent's own framing
anticipated ("issuance fires when `isBorrowerEligible`+`decideColonySpawn`-style gate says yes; repayment
fires when a borrower claims a repayment tx happened"). **Decision: TWO separate top-level REQs, REQ-115
(issuance) and REQ-116 (servicing), never one conflated function** — because folding issuance's own
dual-lock, kill-switch, and two-phase-disbursement sequence into the SAME function as REQ-108/109's own
single-lock, no-disbursement, repayment/default sequence would either (a) force a single function to
branch internally on "am I issuing or am I servicing," which is itself a form of the judgment/decision
logic REQ-103's bookkeeping-only discipline forbids an orchestrator from containing, or (b) silently
imply the two share a lock scope they structurally do not (REQ-106's own PROP-106i explicitly forbids
this). Within the servicing side, `executeRepaymentClaim` and `executeDefaultDetectionSweep` ARE named as
two separate functions rather than one, despite sharing REQ-116's own single REQ number and the identical
`` `loan_${loan_id}` `` lock — because they have two genuinely different triggers (an external repayment
claim vs. a scheduled sweep) and two genuinely different input shapes (one `loan_id`+`txHash` vs. a
colony-wide scan) — but they are specified TOGETHER, under one REQ, because REQ-108's own PROP-108d proof
obligation is literally the claim that these two, launched concurrently against the SAME `loan_id`, never
both append — a property that can only be tested, and can only be reasoned about correctly, when both
functions are specified as one coherent pair sharing one lock discipline, not two independently-evolving
REQs that might drift apart on how they use that shared lock.

## Scope

This sprint delivers:
1. REQ-115's `executeLoanIssuanceAttempt` (new `~/anicca/skills/economy/lending/lib/lending-orchestrator.mjs`),
   wiring sprint-1's pure/narrow modules (`lending-gate.mjs`, `lending-path.mjs`) plus the two reused
   effectful primitives (`lock.mjs::withGigLock`, `escrow.mjs::payViaFacilitator`) and sprint-1's own
   `lending-verify.mjs::reconcileProvisionalDisbursement` per its own canonical 9-step call order.
2. REQ-116's `executeRepaymentClaim` and `executeDefaultDetectionSweep` (same new module), wiring
   sprint-1's `lending-verify.mjs::verifyRepayment` and `lending-gate.mjs::detectDefaultedLoans`/
   `adjustBalancesForOutstandingDebt` into two real, per-loan-lock-protected servicing flows.

Files touched (all in `~/anicca`, repo `github.com/Daisuke134/anicca`, branch `main`) — exact list
finalized at Phase 2a (RED), expected to include: `skills/economy/lending/lib/lending-orchestrator.mjs`
(new), plus test files under `skills/economy/lending/lib/__tests__/`. `lending-gate.mjs`,
`lending-path.mjs`, `gojo-read.mjs`, `lending-verify.mjs` are all reused UNMODIFIED (sprint-1 delivered
and hardened them; this sprint calls them, never edits their exported signatures or internal logic,
matching CRIT-201's own "no incidental edits" requirement).

## Deferred-obligation disposition (contracts/sprint-1.md's 19, reconciled against this sprint's own scope)

All 19 of contracts/sprint-1.md's own deferred obligations are targeted for closure this sprint, via the
REAL orchestrator functions REQ-115/REQ-116 add — none require a real, live token spend to prove (every
one is closeable via structural/unit/integration-test proof against sprint-1's own already-injectable I/O
boundaries, `payViaFacilitator`/`reconcileProvisionalDisbursement`'s own mockable RPC calls):

**15 issuance-side** (REQ-115): PROP-106a, PROP-106b, PROP-106n, PROP-106e (Tier-2 half), PROP-106f,
PROP-106g, PROP-106h, PROP-106k, PROP-106l, PROP-106o, PROP-106p, PROP-106i, PROP-105h, PROP-114c,
PROP-112a.

**4 servicing-side** (REQ-116): PROP-108c, PROP-108d, PROP-109e, PROP-109g.

**Explicitly NOT among the 19, and explicitly NOT targeted this sprint (Tier-3, genuinely requires a
real, live USDC spend)**: PROP-108a (REQ-108's own pre-existing Tier-3 live-E2E obligation — a real
disbursement transfer plus a real repayment transfer, independently re-verified via a separate RPC call).
This sprint's own REQ-115/REQ-116 are exactly the code that makes PROP-108a ATTEMPTABLE for the first
time (sprint-1 had no orchestrator to run it through) — but attempting it is a real-money decision left
to whoever executes this sprint's own Phase 5, made against the colony's actual real-money readiness at
that time, mirroring `anicca-agent-spawn` sprint-2's own CRIT-206 treatment of its own Tier-3 obligations
(PROP-302b/PROP-303b/PROP-401a) — this contract only commits to NOT silently claiming PROP-108a proved via
a fixture, a simulated transfer, or a borrowed artifact from a different feature or chain (CRIT-206).

**Correction (contract-review round 1, resolves FIND-C202)**: despite this section's own already-correct
disposition text above, state.json's own PROP-108a entry (id PROP-025) was found marked
`status:"proved"`/`required:true` — a stale leftover citing sprint-1's own `prop-108a-live-mainnet-e2e.mjs`
harness, which calls `verifyRepayment` directly against one pre-existing historical txHash with
`loanRows:[]` and zero orchestrator involvement (the orchestrator did not exist when that harness ran) —
exactly the "borrowed artifact" CRIT-206 forbids. Corrected to `status:"skipped"`/`required:false`,
matching this section's own already-stated intent. PROP-108a remains genuinely open for a future
checkpoint (this project's own task #28, "P3実deploy検証チェックポイント(Phase5)", or a dedicated
lending-specific equivalent).

## Known residual scope boundary

`executeDefaultDetectionSweep`'s own per-candidate loop (REQ-116's own canonical call order, step 2)
processes candidates sequentially, never in parallel, against the same shared `loans.jsonl` — if, at
Phase 2a (RED), a genuinely concurrent multi-candidate sweep is found to need dedicated integration
coverage beyond a single-candidate-sufficient fixture, that is recorded as a Phase 2c note, not silently
dropped; REQ-108/109's own already-specified per-loan lock discipline (unchanged, unmodified this sprint)
already guarantees correctness for any single candidate regardless of how many others are queued behind
it in the same sweep pass. REQ-101 through REQ-114's own remaining Tier-0/Tier-1 obligations not already
proved by sprint-1 (there are none outside the 19 listed above — sprint-1's own contract already closed
every other originally-deferred obligation, per its own two completeness corrections) are not touched by
this sprint's own scope.

## Phase 2c refactor note (this revision)

`lending-orchestrator.mjs` (399 lines, was 401) had one genuine duplication: the `status: "active"`
row shape (`tx_hash`/`issued_ms`/`due_ms`) was constructed identically at two call sites —
`resolveStaleProvisioning`'s reconciliation-success branch (REQ-106 step 5) and
`runLockedIssuance`'s own disbursement-success branch (REQ-106 step 9). Extracted into one helper,
`activeStatusFields(txHash, nowMs)`, called from both sites via object-spread — no behavior change (same
keys, same values, same relative key order in the appended row). No other duplication met the bar for
extraction (`spawn-orchestrator.mjs`'s own `runStep` helper collapses ~6 repeated try/catch/requireOk
call sites; this module has only one such try/catch, at step 9's disbursement call, which is not
repeated elsewhere, so collapsing it into a helper would not reduce duplication).

The two GREEN-phase implementation notes flagged for critical review were independently re-verified this
phase, against fresh reads of REQ-114/REQ-105 (behavioral-spec.md) and CRIT-204/PROP-116c
(this contract / verification-architecture.md line ~524):
- **Kill-switch tie-break** (`evaluateKillSwitches`'s isolated first call to
  `evaluateOverallDefaultKillSwitch` with neutral `sampleSize`/`totalDefaultedUsd`/`defaultRateUsd`):
  REQ-114's own text states the tie-break between its own switch and REQ-105's cold-start switch is
  explicitly **implementation-defined** ("report whichever reason it evaluates first... since either
  reason alone is already sufficient grounds for refusal") — the isolated-call technique is one valid
  implementation-defined choice among several, reuses only the existing exported function (never a
  second threshold comparison), and is not under test for its specific priority (no test constructs a
  simultaneous cold-start + absolute-loss trip), so it carries zero regression risk either way. Comment
  wording tightened this phase to say "implementation-defined" rather than imply REQ-114 mandates this
  exact order.
- **`await Promise.resolve()` yield before each sweep candidate's lock attempt**: empirically confirmed
  necessary. Removed the yield and ran
  `node --test skills/economy/lending/lib/__tests__/lending-orchestrator.test.mjs` 10 times: the "a
  candidate flagged by step 1's read but found already-repaid at step 2's own fresh re-read is correctly
  skipped, never defaulted" test (line 589) failed 10/10 runs (the sweep, having more synchronous
  pre-lock work, structurally dispatched its lock-acquisition I/O before a concurrently-invoked
  `executeRepaymentClaim` could reach its own first await, deterministically winning the race and
  wrongly defaulting an already-repaid loan). Restored the yield: 3/3 full-suite runs pass 119/119 with
  zero flakiness. The yield only affects WHICH side's lock-acquisition I/O is dispatched first when both
  race for the SAME `loan_id`; it does not touch `withGigLock`'s own atomicity, so it does not weaken
  CRIT-204/PROP-116c's actual guarantee ("exactly one of the two [lock acquisitions] succeeds and
  appends" — REQ-116's own Edge Cases text — never a guarantee about which specific side wins).

No criteria (CRIT-201 through CRIT-207) required changes — their descriptions/passThresholds describe
requirements that remain true unchanged by this refactor (single call-graph root, dual-lock scope,
9-step edge-case coverage, the 19 deferred obligations, PROP-108a's Tier-3 discipline, the Phase 1c
gate). Final: 119/119 tests pass (89 pre-existing + 30 new, matching Phase 2b's own count — refactor
added zero new tests, per the "no behavior change" discipline this phase is held to).
