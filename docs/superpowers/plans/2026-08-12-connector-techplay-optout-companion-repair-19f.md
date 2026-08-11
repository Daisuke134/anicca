# TECH PLAY Hydrated Opt-out Companion Repair Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Superpowers test-driven-development. Sol owns plan/review/live verification/commit; Luna owns the exact two Harness files.

**Goal:** Keep the exact opt-out operation verifiable after TECH PLAY hydrates seven hidden native checkbox companions on the first toggle.

**Measured production DOM:** Before any opt-out mutation, input inspection succeeds. After the first exact role-checkbox changes `aria-checked=true→false`, TECH PLAY adds seven `INPUT type=checkbox` elements. Each companion has empty id/name, `aria-hidden=true`, is visually hidden, is the immediate next sibling of exactly one known visible `BUTTON role=checkbox`, and its boolean `checked` equals that button's `aria-checked`. The existing inspector rejects these valid companions and returns zero controls, so postcondition fails after six answer actions plus the first opt-out. Review/final clicks remain zero.

**Files / soft target:**

- Modify `apps/life-manager/lib/connector-production-browser-harness.js` — about 10–25 LOC.
- Modify `apps/life-manager/lib/connector-production-browser-harness.test.js` — about 35–70 LOC.

## Contract

- [ ] RED fixture reproduces the seven hydrated companions and current zero-control failure.
- [ ] Accept either zero companions before hydration or exactly seven one-to-one companions after hydration.
- [ ] Every accepted companion must be connected, visually hidden, `INPUT type=checkbox`, empty id/name, `aria-hidden=true`, immediate next sibling of one exact known opt-out button in the same parent, and `checked` equal to the button's exact `aria-checked` boolean.
- [ ] Reject partial/extra/duplicate mapping, visible companion, wrong tag/type, nonempty id/name, missing aria-hidden, wrong sibling/parent, unknown button id, and checked/aria mismatch.
- [ ] Do not expose label text, value, form data, or private answers.
- [ ] Re-run Harness + TECH PLAY workflow, syntax, diff check, mutation proof, fresh Sol review.
- [ ] Repeat authenticated live E2E: six answers + seven opt-outs completed, review submittable, review/final click 0, private projection leak 0, owned page cleanup.
