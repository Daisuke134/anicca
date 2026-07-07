# Resolution Notes — Phase 1c spec review, iteration 7

feature: `anicca-agent-lending` · mode: strict · review verdict: FAIL (3 findings — 2 major, 1 minor) ·
this revision resolves all three. Files touched: `specs/behavioral-spec.md`,
`specs/verification-architecture.md`. Neither `state.json`, the reviews manifest, nor any verdict file was
touched, per the task's own constraint — only the two spec files were edited.

---

## FIND-601 (major) — re-verify both kill-switches inside the lock-protected fresh-check

**Problem restated:** REQ-106's own lock-protected fresh-check (added for FIND-401 to re-verify
REQ-101/102/105's sizing/eligibility against a fresh, post-lock read of `loans.jsonl`) never re-verified
either kill-switch (`evaluateColdStartKillSwitch`/`evaluateOverallDefaultKillSwitch`) — both were only
checked once, on a snapshot taken BEFORE either lock (lender or borrower) is acquired. Because both
kill-switches are colony-wide (not scoped to the specific lender/borrower pair whose locks are held), two
concurrent, non-lock-contending issuance attempts (different lender AND different borrower) could each pass
their own pre-lock check and both slip through even if a kill-switch tripped in the interim — the same class
of TOCTOU race FIND-401 already closed for borrower eligibility, left open here for the kill-switches' own
pause decisions.

**`specs/behavioral-spec.md` changes:**
- New subsection **"Kill-switch re-verification inside this SAME lock-protected fresh-check"** inserted into
  REQ-106's "Cross-lender same-borrower exclusion" area, lines **1123-1147**: specifies that, while BOTH
  locks are held, and as part of the SAME fresh-read critical section already used for
  REQ-102(a)-(d)/REQ-101/REQ-104/105, THE SYSTEM SHALL ALSO re-evaluate `evaluateColdStartKillSwitch` (for a
  cold-start request) and `evaluateOverallDefaultKillSwitch` (for every request) against that SAME fresh
  read, refusing (`reason:"cold_start_paused"`/`"overall_default_paused"`) if either now returns
  `paused:true`, regardless of the earlier pre-lock result.
- New Edge Case, lines **1483-1491**: the kill-switch-flips-between-pre-lock-check-and-lock-acquisition
  race scenario, explicitly resolving FIND-601.
- Acceptance Criteria ordering bullet updated, lines **1518-1522** (originally the "FRESH read →
  REQ-102(a)-(c) → REQ-101 → REQ-104/105 → n → disbursement" bullet): now inserts "BOTH kill-switches'
  fresh re-check" into the critical-section ordering.
- PROP-105h's own AC bullet (REQ-106 Acceptance Criteria) extended, lines **1596-1604**, to require a
  SECOND, separate call site inside the lock-protected fresh-check.
- PROP-114c's own AC bullet extended similarly, lines **1605-1619**, plus the new AC bullet for
  **PROP-106p** at lines **1620-1627** — the binding race fixture: kill-switch healthy at the pre-lock
  check, flips to paused before the fresh re-check (simulated concurrent state change) → issuance refused
  at the fresh re-check, not merely the initial one.
- Non-functional requirements paragraph (money-safety bullet) updated to mention both kill-switches being
  re-verified inside the lock (near the REQ-114 dollar-monitoring sentence, ~line 330 area).
- Purity boundary table row for "Colony-wide default kill-switch enforcement" updated (line ~292) to state
  the function is now re-evaluated a second time inside the lock-protected fresh-check.
- Header/changelog: `## Changelog (iteration 7 → current, this revision)` table (line 93) documents FIND-601
  alongside FIND-602/603; top-of-file `revision:` metadata bumped from "iteration 6" to "iteration 7".

**`specs/verification-architecture.md` changes:**
- `evaluateColdStartKillSwitch` purity-map row (line 19) and `evaluateOverallDefaultKillSwitch` purity-map
  row (line 30) both extended to note the second, lock-protected re-evaluation.
- PROP-105h (line 131) and PROP-114c (line 135) rows extended: both now require a structural/Tier-0
  confirmation of a SECOND call site inside the lock-protected fresh-check, not merely the pre-lock call.
- **New PROP-106p** row added after PROP-106o (line 152): Tier 2, Required `true`, the concurrency-fixture
  proof requested by the finding — a kill-switch healthy at the pre-lock check whose inputs change
  (simulated concurrent event) before the fresh, lock-protected re-check, asserting refusal at that fresh
  re-check for BOTH `evaluateColdStartKillSwitch` and `evaluateOverallDefaultKillSwitch`.
- Verification Strategy section: Tier-0 paragraph (lines 174-190) and Tier-2 paragraph (lines 212-226)
  updated to cite the extended PROP-105h/PROP-114c and the new PROP-106p.
- Gate section: Gate (2) and Gate (3) (lines 251-345 area) both updated with an explicit adversary
  confirmation requirement for the fresh, lock-protected kill-switch re-check and PROP-106p's own race
  fixture.

---

## FIND-602 (major) — close the volume-dilution loophole in REQ-114's metric

**Problem restated:** REQ-114's dollar-weighted default-rate RATIO (`defaultRateUsd = totalDefaultedUsd /
totalIssuedUsd`) correctly resists dilution by loan COUNT, but not by loan VOLUME: once `sampleSize >= 10`,
a large volume of OTHER, unrelated, healthy large loans completing around the same time as a genuine large
bust-out default can dilute `defaultRateUsd` below the `0.20` threshold, defeating the exact scenario
REQ-114 exists to catch.

**Fix:** a SECOND, complementary, absolute-dollar-loss-within-a-rolling-window signal,
`computeRecentDefaultLossUsd`, feeding a third OR-branch inside `evaluateOverallDefaultKillSwitch`. Because
it is an absolute sum (never a ratio), it cannot be diluted by unrelated loan volume. Threshold/window
chosen by reusing this document's own existing order-of-magnitude anchors: `RECENT_DEFAULT_LOSS_THRESHOLD_USD
= 5.00` (== `maxLoanUsd`/`perCitizenReserveUsd`'s existing `$5.00` anchor — so ONE bust-out default at the
maximum possible loan size alone trips it) and `RECENT_DEFAULT_LOSS_WINDOW_DAYS = 14` (== the existing
`LOAN_REPAYMENT_WINDOW_DAYS` colony timescale). Both are honestly flagged as unvalidated starting
placeholders, matching this spec's own existing convention for the `0.20` ratio threshold and REQ-105's own
kill-switch threshold.

**`specs/behavioral-spec.md` changes:**
- New paragraph **"A SECOND, DIFFERENT dilution failure mode..."** inserted into REQ-114, lines **840-859**:
  states the volume-dilution problem concretely (9 healthy $5.00 loans + 1 $5.00 default → ratio 0.10,
  below threshold) and introduces `computeRecentDefaultLossUsd({loanRows, nowMs, windowDays})`.
- Definition paragraph for `computeRecentDefaultLossUsd`, lines **861-876**.
- New **"Threshold and window, honestly grounded"** paragraph, lines **878-896**: grounds
  `RECENT_DEFAULT_LOSS_THRESHOLD_USD=5.00`/`RECENT_DEFAULT_LOSS_WINDOW_DAYS=14` in the document's existing
  `maxLoanUsd`/`LOAN_REPAYMENT_WINDOW_DAYS` anchors, flags them as unvalidated placeholders.
- **"Kill-switch enforcement"** paragraph rewritten, lines **920-949**: `evaluateOverallDefaultKillSwitch`'s
  signature extended with `totalRecentDefaultLossUsd`; pause rule now THREE conditions (existing ratio
  branch, existing small-sample branch, NEW absolute-loss branch); either signal alone sufficient to pause;
  REQ-106's own external refusal reason string (`"overall_default_paused"`) unchanged, only the internal,
  diagnostic `reason` enum gains new values.
- REQ-109 gains the `defaulted_ms` field definition (needed for the rolling-window check), lines
  **1970-1980** (inserted into the "defaulted" row's own definition paragraph): wall-clock time at the
  moment the `"defaulted"` row itself is appended, mirroring REQ-106's `issued_ms`-precision convention.
- REQ-114 Edge Cases: three new bullets added, lines **997-1010** — the exact volume-dilution scenario the
  finding names; a default outside the window being correctly excluded; multiple small defaults summing
  above the threshold.
- REQ-114 Acceptance Criteria: PROP-114c's own AC bullet extended (see FIND-601 section above, same edit)
  to require the real code compute+pass `computeRecentDefaultLossUsd`'s output; four new AC bullets added,
  lines **1036-1060** — `computeRecentDefaultLossUsd`'s own correctness (new PROP-114e), the
  dilution-defeat fixture proving the absolute signal catches what the ratio alone misses (new PROP-114f,
  the requirement's own core proof), and the extended THREE-branch `evaluateOverallDefaultKillSwitch`
  fixture set (extends PROP-114b).
- Purity boundary table row for "Colony-wide, dollar-weighted default-rate monitoring" (line ~289) and
  "Colony-wide default kill-switch enforcement" (line ~292) both updated to mention the new sibling
  function and the extended kill-switch signature.
- Non-functional requirements paragraph updated (REQ-114 sentence, ~line 327-330) to mention the two
  complementary, independently-sufficient signals.
- Header/changelog: documented in the new `## Changelog (iteration 7 → current, this revision)` table
  (line 93).

**`specs/verification-architecture.md` changes:**
- **New purity-map row** for `computeRecentDefaultLossUsd` inserted after the `computeOverallDefaultRateUsd`
  row (line 28).
- `evaluateOverallDefaultKillSwitch` purity-map row (line 30) rewritten: signature now includes
  `totalRecentDefaultLossUsd`, pause rule now THREE conditions.
- PROP-114b row (line 133) rewritten: THREE-condition pause rule, new fixture isolating the third branch.
- PROP-114c row (line 135) extended: real code must also compute+pass `computeRecentDefaultLossUsd`'s
  output (clause (e) in the structural check).
- **New PROP-114e row** (line 136): `computeRecentDefaultLossUsd`'s own correctness fixture, Tier 1.
- **New PROP-114f row** (line 137): the dilution-defeat proof fixture requested by the finding, Tier 1.
- Verification Strategy Tier-1 paragraph (lines 201-206) updated to cite PROP-114e/PROP-114f.
- Gate (2) (lines 269-303 area) updated with an explicit adversary confirmation requirement for the
  dilution-defeat fixture (PROP-114f) and the honest-placeholder framing for the new threshold/window.

---

## FIND-603 (minor) — fix the missed cross-reference

**Problem restated:** the self-loan-exclusion cross-reference (REQ-106's own Edge Case and Acceptance
Criterion, added for FIND-402) named only `evaluateColdStartKillSwitch`, never
`evaluateOverallDefaultKillSwitch`, even though the self-loan check structurally precedes both.

**`specs/behavioral-spec.md` changes:**
- REQ-106 Edge Case (self-loan attempt), line **1440-1444** (originally "before REQ-101's surplus
  computation, before `evaluateColdStartKillSwitch`, and before EITHER lock..."): now reads "before
  `evaluateColdStartKillSwitch` AND `evaluateOverallDefaultKillSwitch`..." — resolves FIND-603.
- REQ-106 Acceptance Criterion (self-loan check runs first), line **1514-1517**: now reads "runs FIRST —
  before either lock is acquired, and before EITHER `evaluateColdStartKillSwitch` OR
  `evaluateOverallDefaultKillSwitch` is ever evaluated (resolves this revision's own spec-review iteration-7
  FIND-603) — refusing a self-loan candidate at zero cost..."
- Header/changelog: documented in the new changelog table (line 93).

No changes were required in `specs/verification-architecture.md` for FIND-603 — the finding was scoped
exclusively to the two named prose cross-references in `behavioral-spec.md`, and no verification-architecture
row repeats the same incomplete enumeration.

---

## Files touched (paths)

- `/Users/anicca/anicca-project/.vcsdd/features/anicca-agent-lending/specs/behavioral-spec.md`
- `/Users/anicca/anicca-project/.vcsdd/features/anicca-agent-lending/specs/verification-architecture.md`

No other file was modified. `state.json`, the reviews manifest, and verdict files were left untouched per
the task's own instruction.
