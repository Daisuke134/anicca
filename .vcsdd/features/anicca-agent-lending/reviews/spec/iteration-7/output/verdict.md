# Spec Review Verdict — anicca-agent-lending — Phase 1c — iteration 7

**Overall verdict: FAIL**

Fresh-context review with zero prior conversation history. Read `specs/behavioral-spec.md` (2013 lines,
full), `specs/verification-architecture.md` (415 lines, full), and re-read
`~/anicca/skills/economy/gig/lib/lock.mjs` (209 lines, full) directly from disk this session.

## Prior findings (iteration 6) re-verification

| Finding | Status |
|---|---|
| FIND-501 (false deadlock-avoidance rationale) | **Genuinely resolved.** Fresh re-read of `lock.mjs` confirms `acquire()`/`withGigLock` is a single, non-blocking, fail-fast attempt with no retry-with-wait loop anywhere — classical hold-and-wait deadlock is structurally impossible regardless of lock-acquisition order. Grepped every "deadlock" occurrence in both spec files; zero surviving false claims remain — every mention is now the corrected framing. |
| FIND-502 (REQ-114 wiring) | **Genuinely resolved for the specific gap it named.** New REQ-114 is not a bare, unconnected pure function — REQ-106's own Acceptance Criteria states a new Tier-0 proof obligation, PROP-114c, requiring a direct control-flow read confirming the REAL production issuance code calls `evaluateOverallDefaultKillSwitch`, mirroring PROP-105h's real-source-read discipline exactly (the same rigor that closed FIND-303 for the cold-start switch), and Gate item (2) explicitly forbids the adversary from accepting a mocked-caller fixture as sufficient evidence. This closes the "exists but never proven called" gap FIND-303 previously caught. However, this fresh, skeptical pass over the newly-written REQ-114 section surfaced two **new, distinct** defects in this same area — see FIND-601 and FIND-602 below. |
| FIND-503 (stale changelog) | **Genuinely resolved.** Header and changelog tables now run through "iteration 6 → current, this revision" with no gap. |

## New findings this iteration

- **FIND-601** (verification_readiness, major): Both kill-switches (`evaluateColdStartKillSwitch` and the
  new `evaluateOverallDefaultKillSwitch`) are evaluated exactly once, on a snapshot read taken *before*
  either lock is acquired — the spec's own critical-section ordering (behavioral-spec.md:1344-1349) lists
  a later, lock-protected *fresh* re-read that re-verifies REQ-102(a)-(d), REQ-101, and REQ-104/105
  *sizing*, but never re-verifies either kill-switch's *pause decision* against that fresh read. Because
  both monitors are colony-wide (not scoped to the specific lender/borrower whose locks are held), two
  concurrent issuance attempts for two different lenders and two different borrowers — explicitly
  documented elsewhere as proceeding with zero lock contention — can each read the same pre-pause snapshot
  and both proceed to disburse in the exact window a just-tripped colony-wide kill-switch should be
  refusing "ANY new loan." This is the same class of TOCTOU race FIND-401 already found and fixed for
  borrower eligibility, but the fix was never applied to either kill-switch. PROP-105h/PROP-114c codify
  this gap rather than close it — neither requires the call to use the fresh, lock-protected read.

- **FIND-602** (spec_fidelity, major): REQ-114's own stated purpose is closing a bust-out pattern where an
  established borrower defaults on its single largest loan. The spec explicitly defends against dilution
  of this signal by loan *count* (many small loans alongside one big default), but never addresses or
  discloses dilution by loan *volume*: once `sampleSize >= 10`, a large default can fall below the `0.20`
  dollar-weighted threshold merely because enough *other*, unrelated, healthy large loans also reached
  terminal status — precisely the state a maturing colony (the entire point of REQ-105's doubling ladder)
  will eventually reach. This is a different failure mode from the one the spec's own worked fixtures and
  edge cases test, and it is nowhere flagged as an open/accepted limitation the way this document
  meticulously discloses every other risk it carries.

- **FIND-603** (spec_fidelity, minor): The pre-existing self-loan-exclusion cross-references (written for
  FIND-402, one revision before REQ-114 existed) were not updated this revision to also name
  `evaluateOverallDefaultKillSwitch` alongside `evaluateColdStartKillSwitch` — likely harmless in substance
  ("BEFORE ANY other step" is already exhaustive) but a genuine, checkable incompleteness in how REQ-114
  was integrated into the rest of the document.

## Dimension verdicts

| Dimension | Verdict | Findings |
|---|---|---|
| spec_fidelity | FAIL | FIND-602, FIND-603 |
| verification_readiness | FAIL | FIND-601 |

**overallVerdict: FAIL** (any FAIL dimension fails the whole review).
