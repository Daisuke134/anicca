# Spec Review Verdict — anicca-agent-lending — Phase 1c — iteration 8

**Overall verdict: FAIL**

Fresh-context review, zero prior conversation history. Read `specs/behavioral-spec.md` (2213 lines, full,
in two passes) and `specs/verification-architecture.md` (449 lines, full, in two passes) directly from
disk this session. Read all three iteration-7 findings (FIND-601/602/603) in full before re-checking them
against the current spec text.

## Prior findings (iteration 7) re-verification

| Finding | Status |
|---|---|
| FIND-601 (kill-switches evaluated only pre-lock, TOCTOU race) | **Genuinely resolved.** The critical-section ordering now explicitly re-evaluates BOTH `evaluateColdStartKillSwitch` and `evaluateOverallDefaultKillSwitch` inside the SAME lock-protected, fresh-read critical section already used for REQ-102(a)-(d)/REQ-101/REQ-104/105's own recheck (behavioral-spec.md:1123-1149, 1483-1492). PROP-105h/PROP-114c are both extended to require a second, real-code call site inside that fresh-check, not merely the pre-lock site — the same "real code, not a mock" discipline FIND-303 already established. Every individual issuance attempt performs its own fresh read regardless of lock contention with any other attempt, closing the two-different-lenders/two-different-borrowers race the original finding cited. |
| FIND-602 (dilution-by-volume blind spot in REQ-114's ratio) | **NOT genuinely resolved.** The general mechanism (a second, absolute, volume-dilution-immune signal) is genuinely added and wired in. But this fresh pass found the new signal's own threshold comparison (`totalRecentDefaultLossUsd > RECENT_DEFAULT_LOSS_THRESHOLD_USD`, strict `>`) can never be tripped by a single bust-out default at REQ-105's own `$5.00` ladder ceiling acting alone — because the threshold is DELIBERATELY set equal to that same ceiling, and no single loan can ever exceed it. This directly contradicts the requirement's own stated design rationale and its own worked Edge Case, both of which claim a value that merely EQUALS the threshold still trips the pause. See new finding **FIND-701** below — this reopens the exact headline scenario FIND-602 exists to close. |
| FIND-603 (self-loan cross-reference omission) | **Genuinely resolved.** Both the Edge Case and matching Acceptance Criterion now name both kill-switches explicitly. |

## New findings this iteration

- **FIND-701** (spec_fidelity + verification_readiness, **critical**): REQ-114's new absolute-dollar-loss
  kill-switch branch — the SAME revision's own fix for FIND-602 — uses a strict `>` comparison against a
  threshold (`RECENT_DEFAULT_LOSS_THRESHOLD_USD = $5.00`) that is deliberately set equal to REQ-105's own
  loan-size ceiling (`maxLoanUsd = $5.00`), specifically so that "ONE single bust-out default at REQ-105's
  own maximum possible loan size ... is, BY ITSELF, already sufficient to trip this signal"
  (behavioral-spec.md:880-884). Under the literal `>` operator, a single loan at exactly that ceiling
  produces `totalRecentDefaultLossUsd = 5.00`, which is NOT strictly greater than a `5.00` threshold — so
  this exact, headline scenario can never trip the branch through a single default alone. The document's
  own worked Edge Case (line 1002) explicitly computes a value that "EQUALS" the threshold and still
  asserts `paused:true` — directly contradicted by the `>` formula stated seventy-five lines earlier in
  the SAME requirement. Worse: this is the PRIMARY dilution-defeat proof obligation this revision adds to
  resolve FIND-602 (PROP-114f) — its own fixture computes `totalRecentDefaultLossUsd:5.00` and asserts
  `paused:true`, an outcome unachievable by a correct implementation of the requirement's own literal
  formula. The SAME document's own SEPARATE fixture isolating this same branch (line 1064) deliberately
  uses `5.01` — one cent above threshold — proving the spec author elsewhere DOES treat the boundary as
  exclusive. Two internally-inconsistent fixtures for the identical branch, within the same requirement,
  make this a demonstrable defect, not a matter of interpretation. Net effect: because the ratio signal is
  precisely the one FIND-602 already proved can be diluted below `0.20` by co-existing healthy loan volume,
  and the absolute signal can never trip on a single max-size default alone, the EXACT bust-out scenario
  REQ-114's own rationale (lines 807-838) exists to close can still slip through both signals simultaneously
  whenever the bust-out default lands at exactly `$5.00` rather than an accumulation of smaller defaults.

- **FIND-702** (verification_readiness, major): REQ-109's new `defaulted_ms` field (added this revision to
  feed REQ-114's rolling-window signal) is defined only in prose. REQ-109's own Acceptance Criteria section
  contains zero test or structural check binding the REAL, production default-append code to actually set
  this field when it appends a `"defaulted"` row. Every one of the 9 (behavioral-spec.md) + 3
  (verification-architecture.md) occurrences of `defaulted_ms` is either the prose definition or a
  pure-function fixture test (PROP-114e/PROP-114f) that supplies `defaulted_ms` as already-correct literal
  fixture data — never a real-source-read confirming the actual append call site populates it, the same
  "real code, not a mock" discipline PROP-105h/PROP-114c already apply to the kill-switch call sites two
  sections earlier in this SAME document. An implementation could pass every stated REQ-109 and REQ-114
  PROP while the real append code never sets `defaulted_ms` (a simple omission or field-name typo) — every
  real `"defaulted"` row would then have `defaulted_ms === undefined`, and per REQ-114's own fail-closed
  convention, `computeRecentDefaultLossUsd` would silently treat every real default as outside its window,
  making the entire new absolute-loss defense permanently, silently inert in production while every stated
  proof obligation still passes.

## Dimension verdicts

| Dimension | Verdict | Findings |
|---|---|---|
| spec_fidelity | FAIL | FIND-701 |
| verification_readiness | FAIL | FIND-701, FIND-702 |

**overallVerdict: FAIL** (any FAIL dimension fails the whole review).

## Method note

No positive summary is offered for any dimension: both FAIL, and the reasons are stated above with exact
line citations against `specs/behavioral-spec.md` and `specs/verification-architecture.md`, cross-checked
against each other. This is iteration 8 of a feature that has now FAILed 8 consecutive Phase 1c passes.
