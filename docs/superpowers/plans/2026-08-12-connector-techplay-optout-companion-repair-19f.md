# TECH PLAY Transient Hydration Stability Repair Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Superpowers test-driven-development. Sol owns plan/review/live verification/commit; Luna owns the exact two Harness files.

**Goal:** Keep exact answer and opt-out postcondition verification stable while TECH PLAY briefly injects bounded auxiliary inputs after a form mutation.

**Measured production DOM:** Stable input DOM has 65 selector nodes and inspection returns 49 controls. Immediately after a scalar fill or opt-out toggle, the page can transiently inject 88 auxiliary `INPUT type=text` performance/metadata nodes, producing 153 nodes for the same selector. The existing hard bound is 150, so an immediate post-inspection returns zero controls even though the intended field changed correctly. The auxiliary nodes disappear again within a short bounded interval and stable inspection returns 49. Seven visually hidden native checkbox companions may remain, but the current role-empty shape is already ignored safely and is not the failing guard. Review/final clicks remain zero.

**Files / soft target:**

- Modify `apps/mr-bot/lib/connector-production-browser-harness.js` — about 12–30 LOC.
- Modify `apps/mr-bot/lib/connector-production-browser-harness.test.js` — about 45–85 LOC.

## Contract

- [x] RED action fixture makes the first post-inspection return zero controls from an oversized transient DOM, then returns the exact stable 49 controls without another mutation.
- [x] After an operation reports success, poll only the same page/candidate inspector for a short injected interval. Success still requires the exact token/kind/label/question and `completed:true` on the same join URL.
- [x] Bound polling by injected clock/sleep or fixed small constants. Never raise the 150-node inspector limit, accept an oversized observation, repeat the DOM mutation, or call the external model proposer.
- [x] Zero controls that never stabilize, page/candidate drift, inspector throw, timeout, and stable wrong postcondition remain failed.
- [x] Keep the role-empty hidden native companions covered as ignored non-actionable elements; do not add an invented role or broaden checkbox actionability.
- [x] Do not expose label text, value, form data, or private answers.
- [x] Re-run Harness + TECH PLAY workflow, syntax, diff check, mutation proof, fresh Sol review.
- [x] Repeat authenticated live E2E: six answers + seven opt-outs completed, review submittable, review/final click 0, private projection leak 0, owned page cleanup.
