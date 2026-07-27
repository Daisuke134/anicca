# H3 ORG-checkup Implementation Plan

> **For executor:** Use superpowers test-driven-development and verification-before-completion. Execute in this worktree, one RED/GREEN slice at a time.

**Goal:** Make gastric, colorectal, and brain checkups flow through the existing cloud care chain using only each user's measured cadence.

**Architecture:** Extend the existing calendar-history adapter, deterministic classifier, category-bound Places search, and aftercare vocabulary. Reuse the detector, chain, booking gate, and persistence unchanged.

**Tech Stack:** Node.js 20, `node:test`, Google Calendar transport adapter, Google Places adapter, Supabase/PostgREST, Railway.

---

### Task 1: Long-period history contract

**Files:**
- Modify: `apps/life-manager/lib/events-history.test.js`
- Modify: `apps/life-manager/lib/events.js`

1. Write a failing test that default history spans at least 10 years.
2. Write a failing test that the complete-read cap is 10,000 events.
3. Run `node --test lib/events-history.test.js` and confirm RED for the new contracts.
4. Change constants/comments only enough to pass.
5. Run the focused test and confirm GREEN.

### Task 2: Checkup classification

**Files:**
- Modify: `apps/life-manager/lib/care-daily-runtime.test.js`
- Modify: `apps/life-manager/lib/care-classification-real-history.test.js`
- Modify: `apps/life-manager/lib/care-daily-runtime.js`

1. Write failing tests for gastric, colorectal, and brain titles.
2. Pin specificity: `胃内視鏡 クリニック` must be gastric only; `大腸内視鏡 クリニック` colorectal only.
3. Pin unrelated MRI and ordinary restaurant/calendar text as unclassified.
4. Run focused tests and confirm RED.
5. Add specific keyword groups before generic clinic.
6. Run focused tests and confirm GREEN.

### Task 3: Candidate search and aftercare vocabulary

**Files:**
- Modify: `apps/life-manager/lib/care-candidate-search.test.js`
- Modify: `apps/life-manager/lib/care-candidate-search.js`
- Modify: `apps/life-manager/lib/care-aftercare.test.js`
- Modify: `apps/life-manager/lib/i18n.js`

1. Write failing table-driven tests proving each category uses only its bound query.
2. Write failing report tests proving each new care type has a human Japanese label.
3. Run focused tests and confirm RED.
4. Add three search terms, labels, and emoji.
5. Run focused tests and confirm GREEN.

### Task 4: Detector and integration evidence

**Files:**
- Modify: `apps/life-manager/eval/phy-cases.jsonl`
- Modify: `apps/life-manager/lib/care-daily-runtime.test.js`

1. Add deterministic eval cases for a stable annual gastric cadence and stable biennial colorectal cadence.
2. Add no-history / one-visit brain-dock cases that remain silent.
3. Add integration test: actionable checkup reaches category-bound candidate search and scan-chain persist.
4. Add integration test: insufficient/unstable checkup cadence is persisted but never searches/books.
5. Run `node eval/run-phy-eval.js` and focused integration tests.

### Task 5: Full verification and state

**Files:**
- Modify: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`
- Add: evidence file if production proof needs detail

1. Run `npm test`.
2. Run `npm run eval`.
3. Update H3 TODO row and current cursor with exact test/eval evidence.
4. Commit and push the feature branch to `canonical`.
5. Open and merge the PR after required checks pass.
6. Verify Railway deployment SHA equals merged SHA and the health endpoint succeeds.

