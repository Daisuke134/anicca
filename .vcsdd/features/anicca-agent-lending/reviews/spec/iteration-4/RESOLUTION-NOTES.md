# Resolution Notes — Spec Review Iteration 4 (anicca-agent-lending)

Iteration 4 FAILed with 5 findings (3 critical, 2 major): FIND-301, FIND-302, FIND-303, FIND-304,
FIND-305. This document records exactly what changed, per finding, in `specs/behavioral-spec.md` and
`specs/verification-architecture.md`, with the current line ranges of the edited sections. Line numbers
are as of this resolution pass; both spec files grew (behavioral-spec.md 1369 → 1590 lines,
verification-architecture.md 311 → 360 lines) as a direct result of these fixes, so any future citation of
these ranges should be re-verified fresh (the SAME "moving target" discipline REQ-113 already establishes
for the sibling `anicca-agent-spawn` spec applies to this document's own internal cross-references too).

---

## FIND-301 (critical) — third terminal state: follow-up append itself can throw; reconciliation lookup itself can throw

**Grounding read performed first, as directed:** `~/anicca/skills/self/spawn/lib/ledger.js` lines 20-24
(`appendChild` = a plain, synchronous `fs.appendFileSync`, no internal try/catch — confirmed it can
genuinely throw on `ENOSPC`/`EACCES`/transient I/O failure) and `~/anicca/skills/economy/gig/lib/lock.mjs`
lines 187-209 (`withGigLock`'s own `try { return await fn(); } finally { clearInterval(heartbeat); await
release(statePath, lockKey); }` — confirmed the lock is released NORMALLY via `fs.unlink` regardless of
WHERE inside `fn()` an exception is thrown).

**Fix implemented, `specs/behavioral-spec.md`:**
- REQ-106 body, lines 753-771: the sentence that previously gated reconciliation on "a caller that
  reclaims a STALE `loan_${lenderId}` lock" was replaced with a state-driven trigger: BEFORE computing any
  new sequence number, ANY caller (fast-acquire OR stale-reclaim) ALWAYS checks whether the lender's
  highest-numbered row is UNTERMINATED (`"provisioning"` or `"disbursement_uncertain"` with no later
  terminal follow-up), and if so, ALWAYS performs `reconcileProvisionalDisbursement` first — lock state
  (held/stale/cleanly-released) is no longer a precondition at all.
- REQ-106 body, lines 784-810 (new): two new paragraphs — "Ledger-state-triggered reconciliation, not
  lock-state-triggered" (unifies the crash case, the in-process-exception case, and the NEW
  follow-up-append-itself-throws case under one mechanism, explicitly naming `ledger.js`'s own
  `appendChild`/`lock.mjs`'s own `finally` behavior as the grounding) and "A reconciliation lookup that
  itself throws" (specifies the reconciliation lookup's own failure mode: the attempt fails cleanly, zero
  new row, zero sequence-number consumption, lock released normally, and the SAME standing check simply
  re-fires on the next attempt — safe indefinitely since the lookup is read-only).
- REQ-106 body, line ~823-826: the In-process exception paragraph's opening sentence was corrected from
  "the crash-recovery mechanism above is triggered ONLY when..." to "PRIOR to this revision's own FIND-301
  correction... was triggered ONLY when..." so it no longer contradicts the new, broadened trigger above it.
- REQ-106 Edge Cases, lines ~933-946 (new bullets): the follow-up-append-itself-throws case, and the
  reconciliation-lookup-itself-throws case.
- REQ-106 Acceptance Criteria, lines ~986-999 (new bullets): fixtures for both new cases, introducing
  PROP-106k and PROP-106l.
- Purity boundary table row (`nextLoanSequenceForLender`), line 224: updated to state the reconciliation
  trigger is ledger-state-driven, never lock-state-driven.
- Non-functional requirements (money-safety), lines ~247-255: updated to cite FIND-301 alongside FIND-103/
  FIND-201 as jointly resolved by the SAME unified mechanism.

**Fix implemented, `specs/verification-architecture.md`:**
- Row 24 (`nextLoanSequenceForLender`) and row 35 (`verifyRepayment`/`reconcileProvisionalDisbursement`):
  both rewritten to describe the ledger-state-triggered mechanism and both new failure modes.
- New Proof Obligations, lines 130-131: **PROP-106k** (Tier 2 — follow-up-append-itself-throws fixture,
  proves reconciliation still fires via the ordinary fast-acquire path) and **PROP-106l** (Tier 2 —
  reconciliation-lookup-itself-throws fixture, proves clean failure + safe unbounded retry).
- Verification tiers (Tier 2 lists), lines 74-79 and 189-191: both updated to cite PROP-106k/PROP-106l.
- Gate item (3), lines ~256-269: new clause requiring the adversary to confirm the ledger-state-only
  trigger via both new fixtures, explicitly naming the PRIOR "stale lock" precondition as the closed gap.

---

## FIND-302 (major) — "logged as a replay attempt" undefined

**Fix implemented, `specs/behavioral-spec.md`:**
- REQ-108 body, new paragraph "\"Logged,\" precisely defined," lines 1302-1317: states explicitly that a
  rejected replay (same-loan or cross-loan) is recorded EXCLUSIVELY via an out-of-band mechanism (a
  separate audit/trace log or a debug-level log line) and NEVER as a new `loans.jsonl` row — with the full
  "why": every other reduction in this spec (`sumOutstandingPrincipalUsd`, `isBorrowerEligible`'s condition
  (c), `countSuccessfulOnTimeRepayments`, `detectDefaultedLoans`, `computeColdStartRepaymentRate`) treats
  the last-appended row per `loan_id` as authoritative (last-write-wins); a replay-rejection row would
  become the new "last row" for a loan that has not actually changed state, corrupting that convention.
- REQ-108 Edge Cases, lines ~1345-1356 (edited): both the same-loan and cross-loan replay bullets rewritten
  to say "recorded ONLY via the out-of-band audit/trace logging mechanism above, NEVER a new `loans.jsonl`
  row" instead of the ambiguous "logged."
- REQ-108 Acceptance Criteria, lines 1399-1403 (new bullet): asserts both replay fixtures show `loans.jsonl`
  gains ZERO new rows, plus a structural/Tier-0 read confirming `verifyRepayment`'s replay-rejection branch
  never calls `appendChild`.

**Fix implemented, `specs/verification-architecture.md`:**
- PROP-108e row, line 139: extended to state the out-of-band-only logging requirement and why (last-write-
  wins corruption risk), and its test method extended to assert zero new rows plus a structural read.
- Gate item (4), lines ~258-262: new clause requiring the adversary to confirm the "logged" disposition is
  out-of-band, never a new `loans.jsonl` row.

**Scope note:** the finding's own text separately flagged (as "reinforcing the same underlying gap," not as
part of the directed required fix) that this spec lacks a canonical `loans.jsonl` row-schema table and a
discriminator field distinguishing a disbursement-side `txHash` from a repayment-side `txHash`. Per the
task's explicit "Required fixes" scope for FIND-302 (the out-of-band logging clarification only), that
secondary observation was NOT addressed this pass — it was not part of the directed fix, and adding an
unrequested schema table would be scope creep beyond the assigned edit. It remains a known, separate,
not-yet-closed observation from FIND-302's own text if a future review re-raises it.

---

## FIND-303 (critical) — no Tier-0 proof the kill-switch is actually wired into real code

**Fix implemented, `specs/verification-architecture.md`:**
- New Proof Obligation, line 120: **PROP-105h** (Tier 0 — mirrors PROP-106d's/PROP-106i's own
  real-source-read pattern exactly) — requires a structural/Tier-0 source-grep/control-flow read of REQ-106's
  OWN, REAL, production issuance code confirming it imports and calls `evaluateColdStartKillSwitch` for a
  cold-start request BEFORE acquiring the `loan_${lenderId}` lock — never merely a unit test of the pure
  function in isolation (PROP-105g), and never merely an integration test against a MOCKED issuance call.
- PROP-105g's own row, line 119: annotated to state explicitly that it proves the function's correctness
  and the wiring PATTERN via a mock, but does NOT, by itself, prove the real production code is wired.
- Verification tiers (Tier 0 lists), lines 43 and 148-152 (approx): both updated to cite PROP-105h.
- Gate item (2), lines ~222-228 (approx): new clause requiring the adversary to confirm the REAL issuance
  code — not PROP-105g's mocked fixture — actually calls the kill-switch before the lock.

**Fix implemented, `specs/behavioral-spec.md`** (kept consistent with the verification-architecture.md
addition, since REQ-106 is where the real wiring lives):
- REQ-105 Acceptance Criteria, lines ~688-695: the existing mocked-caller fixture bullet annotated to state
  it proves the function/pattern, not the real wiring, with an explicit pointer to REQ-106's own new
  Tier-0 check.
- REQ-106 Acceptance Criteria, new bullet (near lines 957-963, appended after PROP-106i's bullet): states
  the new Tier-0 structural check requiring the real issuance code (not a mock) to import and call
  `evaluateColdStartKillSwitch` before the lock, citing PROP-105h.

---

## FIND-304 (critical) — balance-adjustment composition omits the real 3-step pipeline

**Grounding read performed first, as directed:** `anicca-agent-spawn`'s CURRENT
`.vcsdd/features/anicca-agent-spawn/specs/behavioral-spec.md` REQ-101 (lines 253-423 as of this session),
confirming the REAL pipeline is THREE steps: (1) `filterProductiveCitizens({citizens, ledgerRows, nowMs,
bootstrapWindowDays})` — filters by lifecycle status, attaches no balance field; (2)
`readCitizenBalances({citizens})` (`~/anicca/skills/self/spawn/lib/colony-balances.mjs`) — the ONLY step
that attaches a `balance_i` figure, via public-chain RPC (spec lines 296-309); (3)
`computeColonySurplusUsd({citizens, perCitizenReserveUsd})` — consumes step (2)'s output.

**Fix implemented, `specs/behavioral-spec.md`:**
- Dependencies section, lines ~112-128: rewrote the "runs AFTER `filterProductiveCitizens`'s output"
  two-step description to name all three steps explicitly and state `adjustBalancesForOutstandingDebt` is
  inserted AFTER step (2) `readCitizenBalances` and BEFORE step (3) `computeColonySurplusUsd`.
- Purity boundary table row (`adjustBalancesForOutstandingDebt`), line 223: updated to the same effect.
- REQ-109 body, two edits: the balance-figure citation (near line 1445) corrected from a stale, incomplete
  `anicca-agent-spawn` REQ-101 line-range citation to the real `readCitizenBalances` reference (lines
  296-309, re-read this session); and the "Composition point, precisely stated" rewrite (near lines
  1458-1475) explicitly naming the three-step pipeline and the correct insertion point, replacing the
  incomplete two-step description this finding identified.
- REQ-109 EARS text, line ~1425-1428 area: the "today: `anicca-agent-spawn`'s
  `computeColonySurplusUsd`/`filterProductiveCitizens`" citation extended to name all three steps.

**Fix implemented, `specs/verification-architecture.md`:**
- Row 23 (`adjustBalancesForOutstandingDebt`) and row 36 (the `anicca-agent-spawn` dependency row): both
  rewritten to name the three-step pipeline and the corrected insertion point.
- Gate item (5), lines ~265-274 (approx): rewritten to require the adversary to confirm the composition
  point sits after `readCitizenBalances` and before `computeColonySurplusUsd`, never between
  `filterProductiveCitizens` and `readCitizenBalances`.

---

## FIND-305 (critical) — REQ-112 must reuse `anicca-agent-spawn`'s real, current `coLocatedWithCoordinator` field

**Grounding read performed first, as directed:** `anicca-agent-spawn`'s CURRENT
`specs/behavioral-spec.md` REQ-105 (lines 584-791 as of this session), confirming: (a) real, current seed
data — automaton `homeDir: "/Users/anicca/.anicca"`, Franklin `homeDir: "/Users/anicca/.blockrun"` —
DISTINCT values, not the stale bare `/Users/anicca` this spec previously (wrongly) cited; (b)
`anicca-agent-spawn` has already added a purpose-built `coLocatedWithCoordinator: boolean` field (seeded
`true` for both real citizens, always `false` for spawned children), and its own spec now explicitly states
"co-located does NOT mean same `homeDir`" (resolves that sibling spec's own FIND-501/FIND-703).

**Fix implemented, `specs/behavioral-spec.md`:**
- Dependencies section record-shape citation, lines ~103-113: added `coLocatedWithCoordinator: boolean` to
  the cited registry shape and removed the incorrect "REQ-112 reads `homeDir` for co-location" framing,
  replacing it with an explicit note that REQ-112 now reads `coLocatedWithCoordinator` instead.
- REQ-112 (lines 1049-1155 section): EARS text and title rewritten (lines ~1049-1069 area) to drop the
  false "both `homeDir: \"/Users/anicca\"`" claim; new paragraph "Co-location mechanism, corrected this
  revision" (starting line 1067) states the co-location check is decided EXCLUSIVELY via
  `citizen.coLocatedWithCoordinator === true` for BOTH lender and borrower, cites the real, distinct
  `homeDir` values and the sibling spec's own FIND-501/FIND-703 resolutions as the grounding for why
  `homeDir`-equality was wrong. Edge Cases extended with a `coLocatedWithCoordinator`-malformed-input
  fail-closed case; Acceptance Criteria extended with a structural/Tier-0 check confirming no `homeDir`
  equality comparison exists anywhere in this feature's diff, plus a fixture proving today's real
  automaton/Franklin pair (distinct `homeDir`, identical `coLocatedWithCoordinator: true`) is correctly
  treated as co-location-eligible.
- Purity boundary table row (REQ-112), line 235: updated to reference the corrected mechanism.
- REQ-113 (lines 1155-1234 section): EARS text rewritten to name TWO concrete, separately-confirmed
  re-verification items (the three-step pipeline shape, and the `coLocatedWithCoordinator` field's
  existence/correct population) instead of a generic "re-read the sibling spec" instruction; the
  "field set is stable" Edge Case corrected to acknowledge `coLocatedWithCoordinator` was ADDED and
  `homeDir`'s seed values were CORRECTED after this feature's own iteration-3 citation; Acceptance Criteria
  extended with an explicit bullet requiring both re-verification items as separate, named line items in
  the Phase 2a dated confirmation.

**Fix implemented, `specs/verification-architecture.md`:**
- Row 29 (REQ-112 design-constraint row) and row 36 (the `anicca-agent-spawn` dependency row, shared with
  FIND-304's fix): both updated to require the `coLocatedWithCoordinator`-only mechanism.
- PROP-112a row, line 134: rewritten to require the structural check confirm no `homeDir`-equality
  comparison exists, plus a new fixture proving the real automaton/Franklin pair is correctly treated as
  co-located despite distinct `homeDir` values.
- PROP-113a row, line 149: rewritten to require the two concrete re-verification line items.
- Verification tiers (Tier 0 lists), lines 48-50 and 156-159 (approx): updated to cite the corrected
  PROP-112a/PROP-113a.
- Gate items (10) and (11), lines ~306-319 (approx): both rewritten — item (10) to require confirmation of
  the `coLocatedWithCoordinator`-only mechanism (citing the real, distinct seed `homeDir` values as proof a
  `homeDir`-equality check would have wrongly excluded today's real co-located citizens); item (11) to
  require the two concrete re-verification items be named, not a generic re-read instruction.

---

## Cross-cutting consistency checks performed after all 5 edits

- Confirmed no leftover "Instead, a caller that reclaims a stale ... lock" framing remains uncorrected
  anywhere in `behavioral-spec.md` (grepped for the exact phrase — zero matches after the FIND-301 fix).
- Confirmed no leftover `homeDir`-for-co-location framing remains in the REQ-112 section (grepped the
  section body — zero `homeDir` occurrences left in REQ-112 itself).
- Confirmed every new PROP ID introduced (PROP-105h, PROP-106k, PROP-106l) follows the existing
  PROP-XXX-lettersuffix convention and does not collide with any pre-existing PROP ID in this feature.
- Confirmed both spec files still contain all 13 REQ-XXX section headers with no structural corruption
  (`grep -n "^### REQ-"` returns the same 13 requirements as before this pass), and all edited
  Proof-Obligation table rows remain single-line (no embedded newlines breaking markdown table rendering).
- Did NOT touch `state.json`, any `reviews/` manifest/verdict file, and did not commit or push, per
  instructions.
