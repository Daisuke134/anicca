# TECH PLAY Review Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Superpowers test-driven-development. Sol owns plan/review/live verification/commit; Luna owns the exact two Harness files.

**Goal:** After all exact TECH PLAY answers and opt-outs are complete, activate the one review CTA and prove navigation to the same-event confirmation page without clicking the final application CTA.

**Architecture:** Extend only the existing TECH PLAY Harness branch. The input inspector already binds `techplay_review_<eventId>` only after full DOM validation and marks it submittable only when ticket, answers, and opt-outs are complete. Start a bounded same-event confirm-URL wait before one exact click. After navigation, re-run the shipped confirm inspector and require the unique safe `techplay_final_<eventId>` control. The custom parent loop remains model-free and stops with `final_blocked` at confirm.

**Files / soft target:**

- Modify `apps/life-manager/lib/connector-production-browser-harness.js` — about 30–55 LOC.
- Modify `apps/life-manager/lib/connector-production-browser-harness.test.js` — about 65–105 LOC.

## Contract

- [ ] RED proves completed input page currently stops at `review_blocked` and never reaches confirm.
- [ ] Select review only when it is the unique exact `BUTTON type=submit`, token/event binding matches, `required:false`, `completed:false`, `submittable:true`, and every answer/opt-out is completed.
- [ ] Before clicking, re-inspect the same candidate join page and rebind the exact review control. Reject wrong method/purpose/token/kind/label/state, pending inputs, duplicate/missing locator, page/event/ticket drift, and inspect/locator/click setup failures.
- [ ] Arm a maximum 30-second exact URL wait before the one click. Accept only `https://techplay.jp/event/join/<sameEventId>/confirm` with no query/fragment. Click throw is successful only if the exact navigation wait still proves confirm; otherwise fail.
- [ ] After navigation, run the shipped confirm inspector and require exactly one `techplay_final_<sameEventId>` control. No final click, provider effect readback, Calendar, evidence, factory/router/native order, or schedule change.
- [ ] TECH PLAY fallback performs 13 deterministic inputs + one review action, calls external proposer 0, returns `final_blocked`, and emits private-free 14-action history.
- [ ] Add negative tests for navigation timeout/reject/wrong event/query/fragment, page drift, residual form controls on confirm, and final control drift. Review mutation occurs at most once.
- [ ] Run Harness + TECH PLAY workflow, syntax, diff check, navigation-guard mutation proof, fresh Sol review.
- [ ] Authenticated live E2E reaches exact confirm, exposes one safe final control, final click 0, private scalar projection leak 0, and closes only the owned page.
