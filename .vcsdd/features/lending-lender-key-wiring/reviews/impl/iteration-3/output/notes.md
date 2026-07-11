# impl-review iteration-3 notes — lending-lender-key-wiring (FINAL gate)

Fresh-context adversary, zero builder context, no Bash. Reviewed HEAD 2e91255a via Read/Grep/Glob only.
No `reviews/impl/iteration-3/input/manifest.json` existed at review time — treated
`specs/behavioral-spec.md` + `specs/verification-architecture.md` as authoritative per the standing
adversary protocol, and independently located and read every source/test file the changelog and
iteration-1/iteration-2 findings referenced.

## Verdict: FAIL (2 findings, FIND-201 critical, FIND-202 medium). NO-GO for unconditional production use.

## What I independently re-verified as genuinely fixed (iteration-2's 3 findings)

- **FIND-101 (value-blind Transfer match)**: FIXED. Traced the exact value decode
  (`safeBigIntValue(log.data)` — a plain single-word BigInt parse, no byte-offset ambiguity since
  Transfer's `value` is the event's only non-indexed field) against `expectedValueBase =
  BigInt(Math.round(loanRow.principal_usd * 1e6))`, confirmed this is the IDENTICAL formula
  `defaultDisburse` itself uses for `amountBase` (lending-orchestrator.mjs:328) — no drift. Confirmed
  the rejection test (lending-verify.test.mjs:257-274) and the same-window-two-logs test (276-298) are
  real, not tautological.
- **FIND-102 (double-disburse on stale-window miss)**: FIXED for its own stated scope. Traced
  `reconcileWindowSpanMs` back to the SAME `lookbackBlocks` figure `defaultReconcile` itself resolves
  (`resolveReconcileLookbackBlocks`) — no duplicated/divergent constant. Did the arithmetic by hand:
  9000 blocks * 2s * 1000 = 18,000,000ms = 5h, matches the doc's own claim, no ms/s unit bug. Both
  directions tested. One immaterial, non-blocking observation: the boundary comparison is strict `>`
  (exactly-at-boundary still trusted), untested at that exact boundary — not worth a formal finding
  since `BASE_BLOCK_TIME_SECONDS` is only ever an average approximation of real Base block production,
  so exact-boundary precision was never actually achievable regardless of the comparison operator.
- **FIND-103 (facilitator not proven mainnet)**: FIXED. `preflightFacilitatorMainnet` is live (fresh
  fetch every call, no caching), fail-closed on both an unreachable fetch and a non-mainnet-advertising
  response, and runs BEFORE `payViaFacilitator` on every real `defaultDisburse` call. I independently
  pulled up `services/facilitator/test-facilitator-contract.mjs` (the actual live facilitator's own test
  harness) to confirm the mocked `{kinds: [{network}]}` shape in the new tests genuinely matches the real
  `/supported` contract — it does (`supported.kinds?.some(k => k.network === "eip155:84532")` is the
  SAME shape, just a different network value for testnet). The mock is faithful. I did not, and could
  not (no Bash/network tool), run a live `curl` against the production facilitatorUrl myself — that
  remains an operator-side, out-of-this-review confirmation, but the code-level guard is sound and now
  standing (checked every call), which is the concrete improvement FIND-103 asked for.

## What I found new this iteration

**FIND-201 (critical, implementation_correctness/edge_case_coverage/verification_readiness)** — the
real substance of this review. `resolveStaleProvisioning` has `loanRows` in scope but never forwards it
into its own `reconcile({loanRow: staleRow})` call, and `reconcileProvisionalDisbursement` has no
parameter to receive it even if it were passed — so neither function can apply the SAME
already-credited-tx_hash cross-check `verifyRepayment` already implements two functions away in the
SAME file (`lending-verify.mjs:84-86`, explicitly commented as resolving this codebase's OWN prior
FIND-202). I traced why this specifically matters for THIS protocol rather than being a generic
"any two same-value transfers could theoretically collide" hand-wave: `computeLoanCapUsd` is a FLAT
$0.02 for every cold-start attempt until a borrower's FIRST successful on-time repayment — so repeat
stuck-row cycles to the same struggling borrower (exactly the retry pattern REQ-118b/REQ-120 exist to
support) are GUARANTEED to share both the exact wallet pair and the exact value FIND-101's fix now
trusts as sufficient proof of attribution. Combined with REQ-120's own already-documented possibility of
a false-negative reconcile (specs/behavioral-spec.md:138-151, an accepted, only partially-mitigated
risk), this produces a concrete chain to genuine fund misattribution across two different loan_ids for
the same borrower — not merely a missed reconciliation, an ACTIVE mis-crediting. I checked whether a
loan-id/reference binding is even possible given USDC's plain ERC-20 Transfer event has no memo field:
yes — tx_hash uniqueness IS such a binding, and this exact codebase already implements it correctly one
function away. I do not accept this as a tolerable $0.02-scale residual, because the fix is small,
already-proven-in-this-repo, and the reachable window for the hazard opens on THIS SAME wallet pair's
very next stuck-row cycle (which is imminent, per the trace below).

**FIND-202 (medium, verification_readiness)** — `specs/verification-architecture.md`'s Proof
Obligations table and Verification Strategy prose were never extended past PROP-121b / "5 new tests" to
cover iteration-2's own REQ-122/REQ-123 additions, even though `behavioral-spec.md` itself WAS correctly
updated with those requirements. A real drift between the two governing spec artifacts, non-blocking for
money-safety on its own but a genuine process gap for a feature this close to real money.

## Live production ledger, checked directly

`~/.blockrun/skills/economy/lending/state/loans.jsonl` (read this review, not from a stale citation):
still exactly 2 rows for `loan_Franklin_1` — `provisioning` then `disbursement_uncertain`
(`error: "Cannot read properties of undefined (reading 'slice')"`, `provisioned_ms: 1783744749665`). No
`disbursement_failed`/`loan_Franklin_2`/`active` row exists yet — confirms no real wake has run against
the fixed code as of this review.

## Final-loan trace (task requirement #4)

Traced against `wake-gate.test.mjs:413-496`'s own recovery fixture, which reproduces this exact row's
wallet pair, principal_usd, and error string. The narrow transition (loan_Franklin_1 →
`disbursement_failed`, then a fresh loan_Franklin_2 disbursement in the SAME wake) is safe and correctly
implemented — confirmed by direct code trace, not merely by the test passing. **This specific,
one-time unsticking of loan_Franklin_1 is NOT what this review is blocking.** What is blocked is treating
this fix as sufficient for the colony's ONGOING lending operation, given FIND-201's reachable follow-on
hazard on this exact pair's own next stuck-row cycle.

## Go/No-Go

**NO-GO** as an unconditional final gate. See `verdict.json`'s own `goNoGo` field for the full reasoning
and the recommended fix (reuse `verifyRepayment`'s own already-proven tx_hash replay guard inside
`reconcileProvisionalDisbursement`/`resolveStaleProvisioning`).

## Process note

A `PostToolUse:Write` hook fired after this review's own output writes, stating: "fablize gate observed a
tool failure. Do not report completion until it is fixed, isolated as a known baseline, or explicitly
documented." This adversary has no Bash/shell tool in this review (by design, per the review brief) and
therefore cannot independently investigate or reproduce whatever tool failure that hook is referring to
— it is not something this review's own Read/Grep/Glob/Write actions could have caused, and no error was
returned from any tool call made during this review. Documented here per that hook's own instruction;
the calling agent should investigate this separately from this review's own substantive verdict above.
