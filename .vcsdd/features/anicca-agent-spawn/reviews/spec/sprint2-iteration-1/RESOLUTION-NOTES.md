# Resolution Notes — anicca-agent-spawn sprint-2 Phase 1c iteration 1 → iteration 2

Resolves the 3 findings from `reviews/spec/sprint2-iteration-1/output/verdict.json`
(overallVerdict: FAIL) ahead of iteration 2's re-review.

## FIND-S2-001 (critical, blocking) — step-6 boundary misclassification

**Root cause**: REQ-307's Edge Cases and `verification-architecture.md`'s PROP-307c drew the
"before identity anchor / after identity anchor" boundary at step 5/6, but step 6 IS REQ-204 — the
step that PRODUCES the `agentId` half of the anchor. A failure AT step 6 (e.g. REQ-204's own Edge
Case: registration succeeds but the `Registered` event can't be decoded → "no agentId recorded")
leaves the anchor incomplete, so routing it through `buildChildSpec` (which REQ-206's Edge Case
says THROWS on a half-complete anchor) would produce no ledger row — violating CRIT-203.

**Changes**:
1. `specs/behavioral-spec.md:2714-2739` (REQ-307 Edge Cases) — rewrote both bullets: the first now
   reads "step 1, 2, 3, 4, 5, or 6 (REQ-201/202/203/306/302/303/204)" and explicitly explains why a
   step-6 failure belongs in the minimal-direct-append bucket; the second now reads "step 7, 8, or 9
   (REQ-205/206/305)" and requires step 6 to have GENUINELY SUCCEEDED first.
2. `specs/behavioral-spec.md:2765-2769` (REQ-307 Acceptance Criteria) — the integration-test
   description's "(a) for steps 1-5 ... (b) for steps 6-9 ..." corrected to "(a) for steps 1-6 ...
   (b) for steps 7-9 ...".
3. `specs/behavioral-spec.md` REQ-305's own FIND-2002 Edge Case (originally lines 2562-2568,
   shifted by this edit) — the "before an identity anchor exists" step list corrected from
   "REQ-201/202/203/306/302/303" to "REQ-201/202/203/306/302/303/204", with an added clause noting
   a REQ-204 failure itself means no `agentId` was recorded.
4. `specs/verification-architecture.md` PROP-307c row (originally line 516) — corrected "steps 1-5
   (before an identity anchor exists) ... steps 6-9 (after an identity anchor exists)" to "steps 1-6
   ... steps 7-9 ...", and added a step-6 fixture requirement to the test-method column.

## FIND-S2-002 (moderate) — EARS clause ordering ambiguity

**Root cause**: REQ-307's EARS clause lists "REQ-201 through REQ-206 ... REQ-306 ... deploy ...
REQ-305" as a flat scope catalog, which, read literally, implies REQ-202 precedes REQ-306 — the
opposite of the Canonical call order (step 3 REQ-306 before step 4 REQ-202, required by PROP-202d's
binding). The Canonical call order section and Acceptance Criteria were already correct; only the
EARS clause's own prose was ambiguous in isolation.

**Change**: `specs/behavioral-spec.md:2677-2683` (REQ-307 EARS clause) — inserted a new sentence,
tagged `**(new, sprint-2, resolves FIND-S2-002)**`, immediately after the entry-point function's
module path is named. It states the requirement list is a SCOPE catalog only, is NOT an ordering
statement, and that the Canonical call order section is the SOLE authoritative statement of
execution sequence — per the recommendation, this permanently defers to that section rather than
reordering the EARS clause's own list (avoiding a repeat of the same divergence class later).

## FIND-S2-003 (moderate) — missing Gate entry for REQ-307

**Root cause**: `verification-architecture.md`'s `## Gate` section gives every other REQ group
(e.g. REQ-306 → entry `(8a)`) a dedicated Phase-3 checklist item, but REQ-307/PROP-307a-d had zero
entries anywhere across the section's 11 items, breaking that document's own established
convention.

**Change**: `specs/verification-architecture.md`, inserted a new entry `(8b)` immediately after
`(8a)` (REQ-306's entry) and before `(9)` (REQ-401's entry). It cites PROP-307a/b/c/d by name and
requires the Phase-3 adversary to confirm: the single-call-graph-root structural check (PROP-307a),
the no-judgment-logic structural check (PROP-307b), the per-step failure-recording integration test
using the CORRECTED 1-6/7-9 boundary from FIND-S2-001's fix — explicitly calling out that this is
the corrected boundary, not iteration-1's 1-5/6-9 one (PROP-307c), and the lock-scope integration
test (PROP-307d).

## Revision header — NOT bumped

Both `specs/behavioral-spec.md` and `specs/verification-architecture.md` carry a shared
`**revision**: iteration 19, revised (spec review iteration-19 finding FIND-1803 resolved ...)`
header. This header documents sprint-1's own Phase-1c review-iteration content-revision count
(sprint-1 ran through iteration 21 per the task history, though the header text itself was last
updated at iteration 19's fix). Sprint-2 has its own, separate review-iteration track
(`reviews/spec/sprint2-iteration-1/`, this being sprint-2's iteration-1 → iteration-2 cycle), so
bumping the shared header to reference sprint-2's findings would conflate two independent counters
this document did not previously mix. Left the header untouched; sprint-2's own resolution history
lives in this RESOLUTION-NOTES.md file instead, mirroring how sprint-1's later iterations are
tracked in their own `reviews/spec/iteration-N/` directories rather than always rewriting the
top-of-file header on every single content fix.

## Not touched

- `state.json` — untouched, as instructed.
- No new iteration-2 review directory or manifest created — untouched, as instructed.
