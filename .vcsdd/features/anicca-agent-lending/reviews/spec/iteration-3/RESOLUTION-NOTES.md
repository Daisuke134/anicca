# Spec Review Iteration-3 — Resolution Notes

**feature**: anicca-agent-lending · **round**: iteration-3 → iteration-4 (post-fix) · **日付**: 2026-07-07

Iteration-3's spec review FAILed with 6 findings (3 critical, 3 major). This document records exactly
what changed, per finding, with new/updated line ranges in the two revised spec files:

- `specs/behavioral-spec.md`
- `specs/verification-architecture.md`

No other files were touched. `state.json`, review manifests, and verdict files were left untouched per
instruction.

---

## FIND-201 (critical) — in-process exception bypasses reconciliation

**Root cause confirmed against real source**: `~/anicca/skills/economy/gig/lib/escrow.mjs::settleBody`
(lines 124-140) has no try/catch around `await publicClient.waitForTransactionReceipt({hash: tx})`
(line 135) — a call that runs strictly *after* `/settle` already returned `success:true` (the transfer is
already broadcast). A genuine RPC timeout here throws uncaught out of `payViaFacilitator`, out of the
`fn()` callback passed to `withGigLock`, which (per `lock.mjs` lines 187-209/203-208) releases the
`loan_${lenderId}` lock **normally** (`fs.unlink`, not stale) in its `finally` block. The next caller for
that lender therefore takes the normal fast-acquire path (`lock.mjs` line 156), never the stale-reclaim
path (lines 128-151) — so `reconcileProvisionalDisbursement` (built only for the crash/stale-reclaim case)
never fires, leaving a dangling `"provisioning"` row with an unknown real-world outcome.

**Fix — `behavioral-spec.md`**:
- REQ-106's step-3 sentence (line ~757-760) now names a third terminal status, `"disbursement_uncertain"`,
  for exactly this case.
- The `nextLoanSequenceForLender` treatment sentence (line ~762-767) now also treats
  `"disbursement_uncertain"` rows as an already-claimed, non-reusable sequence number.
- A new paragraph, **"In-process (non-crash) exception during disbursement"** (line ~754-780), specifies:
  `payViaFacilitator` is wrapped in its OWN try/catch *inside* `fn()`; on catching an exception, a
  follow-up row with `status:"disbursement_uncertain"` is appended before `fn()` returns/throws; and
  `reconcileProvisionalDisbursement` (the SAME on-chain lookup already built for the crash/stale-reclaim
  case) is unified to ALSO resolve an `"disbursement_uncertain"` row — triggered by the NEXT issuance
  attempt for that lender, at the start of its own freshly-acquired lock, *not* gated on a stale-lock
  reclaim (since the lock here was never left stale).
- New Edge Case bullet (REQ-106, after the FIND-103 crash bullet) and new Acceptance Criteria bullet
  (new **PROP-106h**, end of REQ-106's AC list) covering the fixture: inject a throw during
  `waitForTransactionReceipt` after a successful `/settle` → assert `"disbursement_uncertain"` appended,
  lock released normally, and the NEXT attempt reconciles before computing `n+1`, with `payViaFacilitator`
  invoked exactly once total.
- Purity boundary overview table (line ~204) and Non-functional requirements bullet (line ~226-231)
  updated to cite FIND-201 alongside FIND-103 (the two failure modes are now one unified mechanism).

**Fix — `verification-architecture.md`**:
- Purity Boundary Map: `nextLoanSequenceForLender` row and `lending-verify.mjs` row (line ~35) updated to
  describe the unified reconciliation mechanism.
- New proof obligation **PROP-106h** (Tier 2, line ~120) with the exact fixture above.
- Verification tiers/Verification Strategy Tier-1/Tier-2 lists and Gate item (3) updated to reference
  PROP-106h and FIND-201.

---

## FIND-202 (critical) — no txHash deduplication, replay risk

**Fix — `behavioral-spec.md`**:
- New paragraph in REQ-108, **"`txHash` uniqueness / replay-rejection"** (line ~1099-1116, between the
  attribution paragraph and the "Per-loan write discipline" paragraph): `verifyRepayment` MUST, before
  crediting any value, read the FULL `loans.jsonl` ledger, collect every `txHash` already recorded on a
  previously-credited repayment row across ALL `loan_id`s, and reject the newly-claimed `txHash` if
  already present — closing both a same-loan replay and a cross-loan replay.
- New Edge Case bullets (REQ-108, after the partial-repayment bullet): same-loan resubmission rejected;
  cross-loan resubmission rejected.
- New Acceptance Criteria bullets (REQ-108, after the `from`-side extension bullet) plus new **PROP-108e**
  fixture: a real, already-credited `txHash` resubmitted against (a) its own `loan_id` and (b) a
  DIFFERENT `loan_id` — both rejected, crediting `0`.

**Fix — `verification-architecture.md`**:
- Purity Boundary Map `lending-verify.mjs` row (line ~35) updated to state the replay-rejection
  requirement and its `loanRows` full-ledger dependency (function signature updated to
  `verifyRepayment({txHash, expectedFrom, expectedTo, rpcUrl, loanRows})`).
- New proof obligation **PROP-108e** (Tier 1/2, line ~129) with the same-loan/cross-loan fixture.
- Verification Strategy Tier-1/Tier-2 lists and Gate item (4) updated to reference PROP-108e and FIND-202.

---

## FIND-203 (critical) — kill-switch contradicts adjacent edge case, zero proof obligation

**Fix — `behavioral-spec.md`**:
- New paragraph in REQ-105, **"Kill-switch enforcement mechanism"** (line ~585-597, inserted right after
  the kill-switch threshold paragraph): names a new pure function,
  `evaluateColdStartKillSwitch({sampleSize, rate, defaultedCount}) → {paused, reason}`, with the exact
  boolean rule (`sampleSize>=10 AND rate<0.80`, OR `sampleSize<10 AND defaultedCount>=1`), and specifies
  REQ-106's issuance step calls it — before acquiring the per-lender lock — for any cold-start
  (`successfulOnTimeRepayments===0`) loan request, refusing with `reason:"cold_start_paused"` when paused.
- The contradictory Edge Case bullet (was: "this spec does not attach a decision rule... a human or a
  future increment interprets the signal") is **rewritten** (line ~627-636) to state the corrected,
  non-contradictory behavior: `computeColdStartRepaymentRate` still always returns the exact rate
  regardless of sample size (unchanged, correct part preserved), but THIS spec now DOES attach the
  binding kill-switch rule stated above — no longer left to a human/future increment.
- New Acceptance Criteria bullets in REQ-105 (line ~659-670, new **PROP-105g**) covering: below-threshold
  at `sampleSize>=10`; single default at `sampleSize<10` (pauses even though the raw rate is itself above
  `0.80`); a healthy case that does NOT pause; and a fixture wiring the paused state into REQ-106's
  issuance step.
- New Edge Case bullet in REQ-106 (line ~854-858, before Acceptance Criteria) confirming a paused
  cold-start request is refused BEFORE the lock is ever acquired.
- Purity boundary overview table gains a new row for `evaluateColdStartKillSwitch` (line ~206).

**Fix — `verification-architecture.md`**:
- New Purity Boundary Map row for `evaluateColdStartKillSwitch` (line ~19).
- New proof obligation **PROP-105g** (Tier 1, line ~112) with the exact fixtures above.
- Verification tiers/Strategy Tier-1 lists and Gate item (2) updated to require the adversary confirm the
  kill-switch is concretely enforced (not merely stated as prose) and the contradiction is resolved.

---

## FIND-204 (major) — disproportionate full-balance exclusion for default

**Fix — `behavioral-spec.md`**:
- REQ-109's body sentence describing `excludeDefaultedBorrowers` (line ~1216-1250) is **replaced**: the
  function is renamed `adjustBalancesForOutstandingDebt({citizens, loanRows}) → citizens[]` and redesigned
  as a debt-proportional BALANCE ADJUSTMENT, never a citizen removal — returns the SAME array at the SAME
  length, reducing ONLY a currently-defaulted borrower's own balance by exactly its own
  `outstandingDefaultedDebtUsd` (last-write-wins sum of `principal_usd - repaid_usd` over that citizen's
  own `"defaulted"` rows as `borrower_id`), clamped at `0`, with every other field/citizen passed through
  unchanged. Explicitly cites `anicca-agent-spawn` REQ-101 (re-read this session, lines 280-283/398-401)
  to confirm `computeColonySurplusUsd` runs on already-attached per-citizen balance figures, so the
  composition can adjust that SAME figure without touching that function's own signature/source.
- New Edge Case bullet (line ~1287-1290) confirming the adjustment is scoped ONLY to
  `anicca-agent-spawn`'s own colony-surplus aggregation, never altering the citizen's real on-chain
  balance or any other computation.
- Acceptance Criteria rewritten (line ~1292-1305, new **PROP-109f**): a $50-balance citizen with a
  $0.022 defaulted debt (REQ-104's smallest possible loan) is adjusted to exactly $49.978, not $0; a
  separate fixture with debt exceeding balance clamps at exactly $0.
- The Dependencies section's own earlier mention (line ~114-116) and the Purity boundary overview table
  row (line ~203) both renamed/rewritten to match.

**Fix — `verification-architecture.md`**:
- Purity Boundary Map row (line ~23) renamed/rewritten for the proportional design.
- **PROP-109b** rewritten (line ~131) to test the proportional/non-removal behavior; new **PROP-109f**
  added (line ~132) with the $0.022-debt and clamping fixtures.
- Remaining stale `excludeDefaultedBorrowers` mentions in PROP-103a, PROP-109c, and the
  `anicca-agent-spawn` composition-dependency row (lines ~36, 102, 133) updated to the new function name;
  two clearly-historical "corrects the prior design" mentions in `behavioral-spec.md` are deliberately
  left as-is (they describe what was WRONG, per this project's own changelog convention).
- Verification Strategy/Gate item (5) and (6) updated to require the adversary confirm the array-length
  invariant and per-citizen proportionality, not a removal.

---

## FIND-205 (major) — REQ-106/108 lock-labeling contradiction

**Fix — `behavioral-spec.md`**:
- REQ-106's own Acceptance Criteria first bullet (was: "...→ REQ-108/109 ledger append) is wrapped by
  withGigLock(...)") corrected (line ~880-885) to say "THIS REQUIREMENT'S OWN two-phase provisional/
  follow-up ledger append... NEVER REQ-108/109's own, separate per-loan ledger append".
- New paragraph, **"Lock-key disambiguation"** (line ~804-813, inserted before REQ-106's Edge Cases),
  states explicitly: REQ-106's own two-phase append is appended ONLY under the per-lender
  `loan_${lenderId}` lock; REQ-108/109's per-loan `loan_${loan_id}` lock governs ONLY their own LATER,
  independent status-transition appends on an already-active loan; the two locks are never both acquired
  for the same append.
- REQ-108's own per-loan-lock paragraph (line ~1160-1168) gains a reciprocal clarifying sentence: "This
  per-loan lock is NEVER acquired, nested, or otherwise involved during REQ-106's own issuance-time
  critical section."
- New Acceptance Criteria bullet, **PROP-106i** (end of REQ-106's AC list), makes the distinction
  independently, structurally checkable (not merely prose).

**Fix — `verification-architecture.md`**:
- `lock.mjs` Purity Boundary Map row (line ~33) already stated the two keys correctly; strengthened with
  an explicit "NEVER acquired during REQ-106's own issuance-time append" clause.
- New proof obligation **PROP-106i** (Tier 0, line ~121).
- Verification tiers/Strategy Tier-0 lists and Gate items (3)/(4) updated to reference PROP-106i and the
  now-corrected disambiguation.

---

## FIND-206 (major) — missing `.toFixed(6)` money-precision convention

**Confirmed against real source**: `~/anicca/skills/economy/ubi/ubi.js::contribute()` line 40
(`const raw = +(totalRealizedProfitUsd * cfg.contributePct).toFixed(6);`) and
`~/anicca/skills/economy/gig/decide.mjs::decideGigAction()` line 44
(`const surplusUsdc = +(balanceUsdc - reserveUsdc).toFixed(6);`).

**Fix — `behavioral-spec.md`**: every dollar-denominated formula this feature introduces now clamps via
the SAME `+(...).toFixed(6)` pattern, with an explanatory sentence citing the two source lines above:
- `computeLenderAvailableUsd`'s formula block (line ~251-258).
- `sumOutstandingPrincipalUsd`'s description (inline note appended to its existing paragraph).
- `sumRecentGojoGiftsUsd`'s description (inline note appended to its existing paragraph).
- `computeLoanCapUsd`'s formula block (line ~508-513).
- REQ-104's `total_due_usd` formula (line ~474-478).
- `adjustBalancesForOutstandingDebt`'s new debt-subtraction arithmetic (introduced by the FIND-204 fix)
  also clamps via the same convention.
- Acceptance Criteria updated to assert against the CLAMPED value: REQ-101's AC intro bullet, REQ-104's
  `total_due_usd` bullet, REQ-105's `computeLoanCapUsd` boundary bullets, REQ-109's new PROP-109f fixture.

**Fix — `verification-architecture.md`**: Purity Boundary Map rows for `computeLenderAvailableUsd`,
`sumOutstandingPrincipalUsd`, `sumRecentGojoGiftsUsd`, `computeLoanCapUsd`, and
`adjustBalancesForOutstandingDebt` (lines ~14-23) all updated to state the clamp; PROP-104a/105a/105b
Tool/Method text updated to assert against the clamped value; Verification Strategy Tier-1 list and Gate
items (1), (2), (5) updated to require the adversary confirm the clamp is genuinely present, not merely
documented.

---

## Post-fix integrity checks performed this session

- Full markdown-table column-count check across both revised files (Python script comparing pipe counts
  per table block) — zero mismatches.
- Fixed-string grep for literal `||` — found exactly one pre-existing occurrence (line 173,
  `process.env.GIG_FACILITATOR_URL || "..."`, inside prose, not a table row); the one place a raw `||`
  was initially drafted inside a table cell (the `evaluateColdStartKillSwitch` Purity Boundary Map row)
  was reworded to plain "OR" text to eliminate any table-parsing ambiguity.
- Grep confirms all 6 FIND-IDs (FIND-201 through FIND-206) are now cited in both `behavioral-spec.md` and
  `verification-architecture.md`, each with a concrete fix, not a placeholder.
- `state.json`, `reviews/spec/iteration-3/output/manifest*`/verdict files, and
  `reviews/spec/iteration-3/input/` were NOT modified, per instruction.
