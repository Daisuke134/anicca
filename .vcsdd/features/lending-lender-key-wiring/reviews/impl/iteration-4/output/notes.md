# impl-review iteration-4 notes — lending-lender-key-wiring (FINAL gate, money-safety exhaustive)

Fresh-context adversary, zero builder context, no Bash. Reviewed HEAD d6d85f12 via Read/Grep/Glob only.
No `reviews/impl/iteration-4/input/manifest.json` existed at review time (same as iteration-3) — treated
`specs/behavioral-spec.md` + `specs/verification-architecture.md` as authoritative per the standing
adversary protocol, and independently located and read every source/test file iteration-3's own findings
referenced, plus the escrow/facilitator boundary iteration-3 did not trace.

## Verdict: FAIL (1 finding, FIND-301, critical). NO-GO for ongoing lending; today's single manual
recovery of loan_Franklin_1 remains safe.

## Task checklist, answered directly

**1. FIND-201 fix: trace the tx_hash replay guard end to end.** loanRows IS now threaded
`resolveStaleProvisioning` (lending-orchestrator.mjs:122,129) → `reconcile({loanRow, loanRows})` →
`defaultReconcile({loanRow, loanRows}, deps)` (line 236) → `reconcileProvisionalDisbursement({loanRow,
loanRows, ...})` on BOTH its test-seam branch (240-246) and its real production branch (251-260) — no
branch drops it. This wiring is independently confirmed by a dedicated test
(`lending-orchestrator.test.mjs:375-407`) that would fail if the forward were removed. The
`alreadyCredited`/`alreadyRecorded` check DOES scan ALL rows in the full ledger (`readLoanRows` returns
every appended line, not just the latest-per-loan-id), so both disbursement-derived and
repayment-derived `tx_hash` values are covered (both are stored under the SAME `tx_hash` field name).
**Case-sensitivity: NOT handled — this is FIND-301, the substance of this review.** Both comparisons
(`lending-verify.mjs:85` and `:175`) are raw `===`, no `.toLowerCase()`, while this same codebase's
`lending-signer.mjs:32-34` `addressesEqual()` explicitly normalizes case for the structurally identical
problem on wallet addresses. **Can a tx already bound to loan A still be counted for loan B?** Only via
the FIND-301 casing gap, not via the wiring itself — the wiring is sound. **Fail-closed on ambiguity?**
Yes — a malformed/non-hex `log.data` fails that log's own match (`safeBigIntValue` returns `null`,
line 123-129), never a false positive; `loanRows` omitted/empty degrades to "no protection" (matches
REQ-124's own documented edge case), never a false rejection.

**2. Residual from iter3: does the guard genuinely close the collision?** Structurally yes (loan-id → tx
binding via tx_hash uniqueness is real and load-bearing per the tests). Substantively, **no** — see
FIND-301: the guard's own money-safety guarantee silently depends on an unverified assumption that
`escrow.mjs`'s facilitator-returned `settle.json.transaction` string and `lending-verify.mjs`'s own
`eth_getLogs`-derived `log.transactionHash` string share identical casing for the SAME real transaction.
The facilitator (`services/facilitator/x402-rs`, per `.gitmodules`) is an external, third-party Rust
codebase not present in this checkout and not controlled by this feature — this codebase cannot and does
not verify or enforce that assumption anywhere. I found real, live-recorded tx hashes in
`skills/economy/gig/README.md`/`SLOT.md` that happen to all be lowercase (weak positive observational
evidence reducing likelihood, not eliminating the gap) — but nothing in code, spec, or tests asserts,
tests, or enforces this, and every new FIND-201 test fixture uses the IDENTICAL literal string on both
sides of the comparison, which cannot catch a cross-format casing mismatch by construction.

**3. Iter2 fixes still intact?** Yes, re-traced and confirmed unchanged in substance:
- REQ-122 exact-value match: `lending-verify.mjs:166-170` (`expectedValueBase`/`safeBigIntValue`),
  unchanged.
- REQ-120/FIND-102 stale-window refusal: `lending-orchestrator.mjs:137-140`
  (`rowAgeMs > reconcileWindowSpanMs(deps)`), unchanged; `reconcileWindowSpanMs` (208-217) unchanged.
- REQ-123 mainnet preflight: `lending-orchestrator.mjs:277-294` (`preflightFacilitatorMainnet`), called
  at line 334 before `payViaFacilitator`, unchanged, still fail-closed, still uncached.

**4. Final first-loan trace, once more.** Live ledger (`~/.blockrun/skills/economy/lending/state/loans.jsonl`)
read directly this review — identical to iteration-3's own citation, still exactly 2 rows, no wake has
run against the fix yet. Traced directly against the current source (not merely citing a test): the crash
happened pre-signing (no HTTP call ever went out), so `loan_Franklin_1` has **no `tx_hash` field at all**
— FIND-301's casing gap is **not reachable for this specific transition**, because there is nothing yet
stored to collide against. The next wake's reconcile call genuinely finds nothing on-chain for this row
(correctly — nothing was ever broadcast); whether it lands `disbursement_failed` (proceed to a fresh
`loan_Franklin_2` disbursement) or refuses `stale_row_beyond_reconcile_window` (requires manual
intervention) depends on the row's exact age at wake time, which this review has no tool to compute
precisely (no `Date.now()` access) — **both outcomes are money-safe** (neither double-spends). The risk
this review blocks is the NEXT cycle after that: once `loan_Franklin_2` reaches `active` via the happy
disbursement path (storing a facilitator-format `tx_hash`), a THIRD stuck row for the same pair would run
its own reconcile directly into FIND-301's unverified casing assumption.

**5. Test integrity.** The counts match exactly what the task brief independently reported (148/148,
250/250) and what `verification-architecture.md`'s own Verification Strategy section now states (14 new
tests across 3 iterations, 148 total). I read every new test body cited above and in `verdict.json` —
none are tautological; each asserts a real, distinguishing outcome (`found:true` vs `found:false`,
`receivedLoanRows` is an array) tied to a specific code branch. The FIND-201 wiring test
(`lending-orchestrator.test.mjs:375-407`) and the two FIND-201 lending-verify tests (301-348) are
genuinely load-bearing for the WIRING and the SAME-CASING replay check — I did not find a test that would
pass even with those specific guards removed. The gap is not that the existing tests are weak; it is that
NO test exists yet for the casing-mismatch scenario FIND-301 identifies, because every fixture author
(reasonably, for a same-mock-RPC scenario) used the same literal string on both sides.

## FIND-202 (verification-architecture.md drift) — confirmed genuinely fixed

Read `specs/verification-architecture.md` directly this review: PROP-122a/b, PROP-123a/b/c, PROP-124a/b
are all present in the Proof Obligations table, the Changelog documents the iteration-3 fix, and the
Verification Strategy paragraph's test count (148 total, 14 new across 3 iterations) matches the task
brief's own externally-verified figure exactly. No remaining drift between `behavioral-spec.md` and
`verification-architecture.md`.

## Go/No-Go

**NO-GO** as an unconditional final gate for the colony's ONGOING lending operation. See `verdict.json`'s
`goNoGo` field. Recommend: normalize `tx_hash` to lowercase at every storage site
(`lending-orchestrator.mjs`'s `activeStatusFields`/repayment-row construction) and every comparison site
(`lending-verify.mjs:85,175`), mirroring `lending-signer.mjs`'s own `addressesEqual()` precedent exactly;
add a casing-mismatch test fixture. Today's single, manually-supervised recovery of `loan_Franklin_1`
itself remains safe to run (it has no `tx_hash` yet to collide against) — this review's NO-GO is about
trusting this protocol for the SUBSEQUENT, repeated cold-start cycles it exists to support, unattended.
