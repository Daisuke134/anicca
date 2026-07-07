# Spec Review Iteration 2 — Resolution Notes

**feature**: anicca-agent-lending · **mode**: strict · **date**: 2026-07-07
**verdict resolved**: FAIL (7 findings: 3 critical, 4 major) → all 7 addressed below, targeted edits only,
no scope creep beyond what each finding required.

Both spec files' headers were bumped to `revision: iteration 3` and a `## Changelog (iteration 2 →
iteration 3)` table was added to `specs/behavioral-spec.md` (lines 27-40) summarizing all 7 resolutions in
one place, mirroring iteration 1's own changelog convention.

Every source file cited by the findings was re-read fresh this session before editing (not assumed from
memory): `~/anicca/skills/self/spawn/run.sh` (full file, its own "provisional ledger row" step-3 comment,
lines 124-140), `~/anicca/skills/economy/ubi/run.sh` (lines 70-109, the hardcoded `anicca-a3cdd4` gojo
sender identity), `~/anicca/skills/economy/ubi/state/gojo-log.jsonl` (its one real row, no sender field),
`~/anicca/skills/economy/gig/lib/lock.mjs` (full file, `withGigLock`/`isLockStale`/`isSafeLockKey`),
`~/anicca/skills/self/founder-loop/record-earn.mjs` (full file, `parseRawLogs` lines 82-88, confirming the
`FIND-704` fix applies ONLY to the `to` topic), `~/anicca/skills/economy/gig/decide.mjs` (full file,
`DEFAULT_LOW_USDC`), `anicca-agent-spawn`'s CURRENT `specs/behavioral-spec.md` (header, lines 1-8: revision
iteration 5, resolved through FIND-401..405) and its CURRENT `state.json` (`gates."1c"`, lines 1968-1987:
iteration 6 review FAILed `2026-07-07T11:02:55.800Z` with FIND-501..504 — a further iteration past what
the iteration-2 findings themselves cited as "current," directly proving FIND-101's own point about
citation staleness).

---

## FIND-101 (critical) — `anicca-agent-spawn` citation stale again (recurrence of iteration-1's FIND-006)

**Fix**: Dependencies section (`specs/behavioral-spec.md`, the `anicca-agent-spawn` bullet, lines 86-123)
rewritten to STOP citing a specific iteration number/FIND-list/gate-verdict as a durable fact. It now
states, in present tense, that `anicca-agent-spawn` is an independently-evolving sibling feature, STILL
MID-VCSDD-PIPELINE at every revision of this document, and explicitly narrates the recurrence: iteration-1's
FIND-006 already showed this citation drifts; this revision's own FIND-101 showed it again, one cycle
later; re-verified while resolving FIND-101, that spec's Phase 1c gate had ALREADY failed a further time
(iteration 6, `2026-07-07T11:02:55.800Z`, FIND-501..504) — a further iteration past the iteration-5 state
FIND-101's own evidence had cited as "current" only minutes earlier. The registry-shape citation itself
(`{id, wallet, walletAddress, fuel, humanDependencies, homeDir}`) is retained but reframed as "read during
THIS revision's own re-verification pass," never a frozen fact.

New **REQ-113** (`specs/behavioral-spec.md` lines 819-857, inserted between REQ-112 and REQ群D): "Dependency
freshness gate — `anicca-agent-spawn` re-verification before Phase 2a." EARS: Phase 2a (test-writing) SHALL
NOT begin until whoever begins it has re-read `anicca-agent-spawn`'s THEN-CURRENT `specs/behavioral-spec.md`
and `state.json` fresh, immediately before starting, and recorded that re-read in writing. This is framed
explicitly as a standing acceptance criterion / Tier-0 process gate, not a one-time citation-accuracy fix.
Edge Cases cover: (a) the registry shape changing further before Phase 2a — REQ-101/102/109/112 must be
revisited; (b) `anicca-agent-spawn`'s Phase 1c still failing when Phase 2a begins — proceed anyway, since
this feature depends only on registry SHAPE/STYLE, not on that spec reaching PASS; (c) a future revision
being tempted to cite a fresher iteration number — REJECTED, the fix is to stop citing a number at all.

- Purity Boundary Map (`specs/behavioral-spec.md` line 215; `specs/verification-architecture.md` line 28,
  inserted after the REQ-112 row): new row, REQ-113 classified "Not code — a process/documentation gate."
- The `anicca-agent-spawn`/`citizens.json` dependency row in `specs/verification-architecture.md` (the
  Purity Boundary Map's "Effectful Shell (existing, out of scope, read-only dependency)" row) reworded to
  drop the frozen citation and point to REQ-113 instead.
- New proof obligation **PROP-113a** (`specs/verification-architecture.md` line 123, Tier 0): "This
  feature's own Phase 2a does not begin until a dated, written confirmation exists that `anicca-agent-spawn`'s
  THEN-CURRENT state was freshly re-read immediately before starting."
- Verification Strategy Tier 0 bullet (verification-architecture.md line ~132) and Gate item (11) (new,
  verification-architecture.md end of Gate section) added: the adversary confirms the mechanism is present
  and enforceable, but does NOT itself need to re-verify `anicca-agent-spawn`'s current state at spec-review
  time — that re-read is Phase 2a's own gate.

## FIND-102 (critical) — gojo gift misattribution (`sumRecentGojoGiftsUsd` lacked `lenderId` gating)

**Fix**: REQ-101 (`specs/behavioral-spec.md`, the `recentGojoGiftsUsd` paragraph, lines 264-291) rewritten:
`sumRecentGojoGiftsUsd` now takes a 4th parameter, `lenderId`, and a new exported constant `GOJO_SENDER_ID
= "anicca-a3cdd4"` (today's real, only gojo sender, confirmed against `run.sh` lines 87-96's hardcoded
`telemetry_files['anicca-a3cdd4']` read). The subtraction applies ONLY when `lenderId === GOJO_SENDER_ID`;
for any OTHER lender it returns `0` UNCONDITIONALLY, regardless of `gojoLogRows` content — documented
honestly as a real limitation of `gojo`'s own current single-sender design, not something this feature can
fully generalize without `ubi.js`/`run.sh` themselves changing.

- REQ-101 Edge Cases (line 320) and Acceptance Criteria (line 338) gained new bullets covering the
  non-`anicca-a3cdd4`-lender-returns-0 case.
- Purity Boundary Map (`specs/behavioral-spec.md` line 205; `specs/verification-architecture.md` line 16):
  `sumRecentGojoGiftsUsd` signature updated to include `lenderId`, with the gating rule stated inline.
- **PROP-101f** (`specs/verification-architecture.md` line 86) updated: now requires a SEPARATE fixture
  proving `lenderId !== GOJO_SENDER_ID` returns `0` even given an in-window gift row.
- Verification Strategy Tier 1 (line 137) and Gate item (1) (line 175) updated to require the adversary
  confirm the gating, not merely the windowing.

## FIND-103 (critical) — double-disbursement risk on crash between settle and ledger append

**Fix**: REQ-106 (`specs/behavioral-spec.md`, new "Crash-safe two-phase issuance record" subsection, lines
631-655, inserted between the `loan_id` generation paragraph and the "Disbursement failure" paragraph)
mirrors `~/anicca/skills/self/spawn/run.sh`'s own real "provisional ledger row (so we never lose track even
if step 4 fails)" pattern (its own step 3, lines 124-140): a PROVISIONAL row (`status:"provisioning"`) is
appended BEFORE `payViaFacilitator` is called, strictly inside the SAME `loan_${lenderId}` lock; a
FOLLOW-UP row (`status:"active"` with `txHash`, or `status:"disbursement_failed"`) is appended after.
`nextLoanSequenceForLender` now treats `"provisioning"`/`"disbursement_failed"`/`"active"` rows for the SAME
`loan_id` as one already-claimed sequence number (last-write-wins) and never reuses `n` while a
`"provisioning"` row lacks a terminal follow-up. A caller reclaiming a stale lock and finding a
still-`"provisioning"` row MUST perform a REAL on-chain lookup (new function `reconcileProvisionalDisbursement`,
mirroring REQ-108/`verifyRepayment`'s own `Transfer`-log-verification machinery) before deciding to retry
or mark the attempt failed — never blindly re-disbursing.

- The "Disbursement failure" paragraph (line ~672) updated to describe the follow-up-row outcome instead of
  "no row appended."
- REQ-106 Edge Cases (two new bullets, lines 685-699) and Acceptance Criteria (two new bullets, lines
  724-733) cover: crash before `payViaFacilitator` is attempted (reclaim finds no transfer, marks failed,
  proceeds at `n+1`); crash after settle succeeds but before the follow-up row (reclaim finds the real
  transfer, recovers it as `"active"`, never disburses twice).
- Purity Boundary Map (`specs/behavioral-spec.md` lines 204, 918 [Security/money-safety NFR];
  `specs/verification-architecture.md` lines 22, 34 [`lending-verify.mjs` row extended with
  `reconcileProvisionalDisbursement`]) updated.
- New proof obligation **PROP-106g** (`specs/verification-architecture.md` line ~101, Tier 2): the exact
  crash-recovery scenario, asserting `payViaFacilitator` is invoked only once total across both callers.
- Verification Strategy Tier 2 (line 151) and Gate item (3) (line 202) updated.

## FIND-104 (major) — repayment/default writes lacked lock discipline

**Fix**: REQ-108 (`specs/behavioral-spec.md`, new "Per-loan write discipline" subsection, lines 922-937,
inserted before Edge Cases) and REQ-109 (line 988, a cross-reference sentence added to the EARS text)
now wrap their own repayment-verification-and-append / default-detection-and-append critical sections in a
NEW per-loan lock, key `` `loan_${loan_id}` `` — deliberately DIFFERENT from REQ-106's per-lender
`` `loan_${lenderId}` `` issuance lock (a different natural key for a different critical section), same
`withGigLock` mechanism, same `LOANS_LEDGER_PATH` statePath. A repayment-verification call and a
default-detection sweep for the SAME `loan_id`, launched concurrently, can never both append.

- REQ-108 Edge Cases (new bullet, line 940) and Acceptance Criteria (new bullet, line 976); REQ-109 Edge
  Cases (new bullet, line 1004) and Acceptance Criteria (new bullet, line 1029).
- Purity Boundary Map (`specs/behavioral-spec.md` line 209; `specs/verification-architecture.md` line 30,
  the `lock.mjs` row): updated to describe BOTH lock keys.
- New proof obligations **PROP-108d** (`specs/verification-architecture.md` line 114, Tier 2) and
  **PROP-109e** (line 119, Tier 0).
- Verification Strategy Tier 0/Tier 2 (lines 131, 154) and Gate items (4)/(5) (lines 214, 218) updated.

## FIND-105 (major) — `from`-topic check overclaimed reuse of `record-earn.mjs`'s pattern

**Fix**: REQ-108's EARS text, part (b) (`specs/behavioral-spec.md`, lines ~889-908) reworded: confirmed
against `record-earn.mjs` lines 82-88 that its own `FIND-704` fix (exact zero-padded-topic equality) applies
ONLY to the `to` topic (`topics[2]`); its `from` topic (`topics[1]`, line 88) is an unchecked substring,
only ever set-membership-tested (line 77), never equality-checked. `verifyRepayment`'s `to`-side check is
now described as a LITERAL REUSE of that proven fix; its `from`-side check is described as an honest, sound
EXTENSION of the same technique to a field `record-earn.mjs` itself never hardened this way — still the
correct, more rigorous design, just honestly attributed.

- REQ-108 Acceptance Criteria (line 972) gained a new bullet: a fixture whose `from` topic is a suffix-only
  match must be rejected, proving the extension is genuinely implemented as exact equality.
- Purity Boundary Map (`specs/verification-architecture.md` line 34, `lending-verify.mjs` row) reworded.
- **PROP-108b** (`specs/verification-architecture.md` line 112) updated with the to-reuse/from-extension
  framing and a new `from`-side rejection fixture.
- Verification Strategy Tier 2 (line 151) and Gate item (4) (line 214) updated.

## FIND-106 (major) — REQ-102/REQ-110 contradiction on `decide.mjs` coupling

**Fix**: REQ-102's EARS text, condition (b) (`specs/behavioral-spec.md`, lines 348-358) reworded:
`BORROWER_LOW_USD` is now stated as this feature's OWN independently-declared constant (default `0.50`),
deliberately set to the SAME numeral as `decide.mjs`'s `DEFAULT_LOW_USDC` for definitional consistency only
— via NO import/code coupling — explicitly cross-referencing REQ-110's own zero-coupling requirement so a
future reader does not mistake "same numeral" for license to add an import. The Dependencies section's
`decide.mjs` bullet (line 186) reworded identically (no more "reuses ... verbatim").

- REQ-102 Acceptance Criteria (new bullet, line 386) and REQ-110 Acceptance Criteria (new bullet, line
  1059, REQ-110 heading at line 1037) added, cross-referencing each other.
- **PROP-110a** (`specs/verification-architecture.md` line 132) updated to explicitly confirm no
  `DEFAULT_LOW_USDC` import exists anywhere in this feature's diff.
- Verification Strategy Tier 0 (line 131-132) and Gate item (8) (line 237) updated.

## FIND-107 (major) — cold-start/first-loan conflation in `computeColdStartRepaymentRate`

**Fix**: REQ-105's "Monitoring plan" paragraph (`specs/behavioral-spec.md`, lines 514-533) rewritten: removed
the false "(i.e. every borrower's own first-ever loan)" parenthetical. The definition is now stated directly
and only as "loans whose originating row had `successfulOnTimeRepayments === 0` at issuance" — RE-DERIVED
per loan by walking each borrower's own strictly-earlier rows (never a stored snapshot field, no new schema
field added). Explicitly notes cold-start CAN recur for a chronically-late-but-eventually-repaying borrower
(their 2nd, 3rd, etc. loan may also qualify) and that this is intentional, since the metric measures
repayment behavior at the zero-reputation cap, not "first loan" specifically.

- REQ-105 Edge Cases (new bullet, line 553) and Acceptance Criteria (new bullet, line 584) added, both
  demonstrating the recurrence case with a concrete fixture shape.
- Purity Boundary Map (`specs/behavioral-spec.md` line 206; `specs/verification-architecture.md` line 21)
  updated with the corrected definition.
- **PROP-105f** (`specs/verification-architecture.md` line 95) updated to require the recurrence fixture.
- Verification Strategy Tier 1 (line 141-142) — no Gate-section wording needed further edits beyond what
  point (2) already required (it already deferred to PROP-105f).
