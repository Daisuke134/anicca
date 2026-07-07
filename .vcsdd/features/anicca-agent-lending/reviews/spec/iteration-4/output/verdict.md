# VCSDD Adversary Verdict — anicca-agent-lending — Phase 1c Spec Review — Iteration 4

**Overall Verdict: FAIL**

**Reviewer:** fresh-context vcsdd-adversary (zero prior conversation context, disk-only review)
**Scope:** `specs/behavioral-spec.md` + `specs/verification-architecture.md` (48 PROP obligations)
**Cross-checked live source:** `escrow.mjs`, `lock.mjs`, `ubi.js`, `decide.mjs`, `ledger.js`, and a FRESH re-read of sibling feature `anicca-agent-spawn`'s current `specs/behavioral-spec.md` and `state.json`.

This feature has now FAILed 4 consecutive Phase 1c spec reviews (21 findings across iterations 1-3, 5 more here). Do not read this as "almost converged" — several of this iteration's findings are the SAME class of defect the prior iteration's own fix claimed to have closed, only relocated one layer deeper.

## Dimension Results

| Dimension | Verdict | Findings |
|---|---|---|
| spec_fidelity | **FAIL** | FIND-304, FIND-305 |
| verification_readiness | **FAIL** | FIND-301, FIND-302, FIND-303 |

## Prior Findings (FIND-201..206) Re-Verification

| Finding | Status |
|---|---|
| FIND-201 (in-process disbursement exception) | **INCOMPLETE** — a new, equally serious gap found one level deeper (FIND-301) |
| FIND-202 (txHash replay) | **PARTIAL** — the manifest's specific question (rejected row = already-credited?) is answered correctly by the spec's own precise wording, but a new, undefined "logged" ambiguity was found (FIND-302) |
| FIND-203 (kill-switch) | **INCOMPLETE** — the internal contradiction is fixed, but the enforcement mechanism has no structural (Tier-0) proof it's wired into real code (FIND-303) |
| FIND-204 (debt-proportional adjustment) | **INCOMPLETE** — the arithmetic is correct, but the composition-point description omits a required pipeline step confirmed present in the sibling's current spec (FIND-304) |
| FIND-205 (lock-key disambiguation) | **genuinely resolved** |
| FIND-206 (money precision) | **genuinely resolved** |

## New Findings

### FIND-301 (critical, verification_readiness, security_surface)
The FIND-201 fix only relocates the in-process-exception hazard one level deeper. Two new, unwrapped failure modes are unaddressed: (1) the `disbursement_uncertain` follow-up `appendChild` call is a plain, unguarded `fs.appendFileSync` (confirmed in `ledger.js:20-24`) that can itself throw, leaving a `"provisioning"` row with no terminal follow-up and a *cleanly-released* (non-stale) lock — a third terminal state the spec's own state machine never names and for which no reconciliation trigger exists; (2) `reconcileProvisionalDisbursement`'s own on-chain RPC lookup, invoked at the start of the next issuance attempt, can itself throw — the spec only describes its two success outcomes, never this failure. This is exactly what the review manifest asked to be checked, and it is confirmed unaddressed.

### FIND-302 (major, verification_readiness, spec_gap)
FIND-202's replay-blocklist correctly handles the manifest's specific question (a rejected row does not count as "already credited"). But the Edge Cases' "logged as a replay attempt" language never specifies whether this is a `loans.jsonl` append (risking corruption of the last-write-wins convention every other computation in this spec depends on) or an out-of-band log. Separately, no canonical `loans.jsonl` row schema is ever given anywhere in this document, and the generic `txHash` field name is never structurally distinguished between disbursement-side rows (REQ-106) and repayment-side rows (REQ-108) — a real risk for PROP-108e's own full-ledger scan.

### FIND-303 (critical, verification_readiness, verification_tool_mismatch)
`evaluateColdStartKillSwitch` has no Tier-0 structural proof obligation requiring the real REQ-106 issuance code to call it. The only backing proof obligation, PROP-105g, is a Tier-1 pure-function test plus a Tier-2 test wired against "a MOCKED REQ-106 issuance call" — never a structural read of the real call site, unlike PROP-106d/PROP-106i's Tier-0 checks for comparable wiring facts in the SAME requirement. As specified, the kill-switch can remain "a computed flag nobody checks" in production.

### FIND-304 (critical, spec_fidelity, requirement_mismatch)
`adjustBalancesForOutstandingDebt`'s stated composition point ("AFTER `filterProductiveCitizens`'s own output and BEFORE `computeColonySurplusUsd`'s own... step") never names `readCitizenBalances` — the sibling feature's own effectful, coordinator-run step (confirmed present in `anicca-agent-spawn`'s CURRENT `specs/behavioral-spec.md` lines 296-309) that must run between those two steps to attach each citizen's `balance_i` figure. Since this lending function is pure/zero-I/O and must reduce an *already-present* balance figure, an implementer following this spec's own complete text (which never names this step) has a real, concrete chance of inserting it in the wrong slot, silently defeating FIND-204's own fix. Confirmed via grep: zero mentions of `readCitizenBalances` anywhere in this feature's own spec docs.

### FIND-305 (critical, spec_fidelity, requirement_mismatch)
REQ-112's own co-location precondition rests on a factually wrong claim, freshly disproven this session: it states "automaton + Franklin, both `homeDir: \"/Users/anicca\"`" as `anicca-agent-spawn`'s "current seed data" — but the sibling's actual current seed data has *distinct* values (`/Users/anicca/.anicca` vs `/Users/anicca/.blockrun`). The bare-shared value the lending spec still cites is explicitly labeled, in the sibling's own spec, as "FIND-501 (critical — the most serious defect found across all six spec-review iterations of this feature)," together with the hardened principle "Co-located (same physical host) does NOT mean 'same homeDir.'" The sibling has since added a dedicated `coLocatedWithCoordinator: boolean` field specifically to solve this problem — a field the lending spec's own registry-shape citation never adopts, and neither spec doc mentions anywhere (confirmed via grep). REQ-112's own PROP-112a verification method ("homeDir is only ever compared for equality") is exactly the approach the sibling has already rejected, and if implemented literally, would incorrectly conclude today's two real, co-located citizens are NOT co-located with each other.

## Positive Evidence (dimensions/portions confirmed sound this pass)

- FIND-205 (lock-key disambiguation): `behavioral-spec.md` lines 804-813, 858-864 and `verification-architecture.md` PROP-106i confirmed internally consistent and structurally checkable.
- FIND-206 (money precision): every dollar-denominated function (`computeLenderAvailableUsd`, `sumOutstandingPrincipalUsd`, `sumRecentGojoGiftsUsd`, `computeLoanCapUsd`, `total_due_usd`) confirmed consistently clamped via `.toFixed(6)` in EARS text and every corresponding Acceptance Criterion/PROP.
- FIND-202's specific manifest question (rejected-row replay handling) confirmed correctly resolved by the spec's precise "previously-verified, CREDITED" scoping language.
- Cross-loan replay via REQ-102's single-outstanding-loan-per-borrower invariant confirmed to make the "genuine" cross-loan-replay attack inherently sequential, not concurrent, closing off a race-condition concern this reviewer independently checked and did not find exploitable.
