# TECH PLAY Review Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Superpowers test-driven-development. Sol owns plan/review/live verification/commit; Luna owns the exact two Harness files.

**Goal:** After all exact TECH PLAY answers and opt-outs are complete, activate the one review CTA and prove navigation to the same-event confirmation page without clicking the final application CTA.

**Architecture:** Extend only the existing TECH PLAY Harness branch. The input inspector already binds `techplay_review_<eventId>` only after full DOM validation and marks it submittable only when ticket, answers, and opt-outs are complete. Start a bounded same-event confirm-URL wait before one exact click. After navigation, re-run the shipped confirm inspector and require the unique safe `techplay_final_<eventId>` control. The custom parent loop remains model-free and stops with `final_blocked` at confirm.

**Files / soft target:**

- Modify `apps/mr-bot/lib/connector-production-browser-harness.js` — about 40–70 LOC.
- Modify `apps/mr-bot/lib/connector-production-browser-harness.test.js` — about 90–140 LOC.

**Authenticated diagnosis:** The exact 30-second `domcontentloaded` URL wait resolves at `/confirm`, but the first immediate confirm inspection can transiently return zero controls while hydration completes; the next read-only inspection exposes the unique final control. Reuse the existing TECH PLAY postcheck budget (20 attempts, 19 sleeps × 25 ms = 475 ms) for confirm observation only. Do not repeat the review click, any input mutation, private resolution, or proposer call.

## Contract

- [x] RED proves completed input page currently stops at `review_blocked` and never reaches confirm.
- [x] Select review only when it is the unique exact `BUTTON type=submit`, token/event binding matches, `required:false`, `completed:false`, `submittable:true`, and every answer/opt-out is completed.
- [x] Before clicking, re-inspect the same candidate join page and rebind the exact review control. Reject wrong method/purpose/token/kind/label/state, pending inputs, duplicate/missing locator, page/event/ticket drift, and inspect/locator/click setup failures.
- [x] Arm a maximum 30-second exact URL wait before the one click. Accept only `https://techplay.jp/event/join/<sameEventId>/confirm` with no query/fragment. Click throw is successful only if the exact navigation wait still proves confirm; otherwise fail.
- [x] After navigation, poll the shipped confirm inspector read-only within the existing 20-attempt/475 ms budget and require exactly one `techplay_final_<sameEventId>` control. Every attempt retains the exact same-event confirm URL and event/canonical/ticket binding. Empty transient observations may retry; no review/input mutation or proposer retry. No final click, provider effect readback, Calendar, evidence, factory/router/native order, or schedule change.
- [x] TECH PLAY fallback performs 13 deterministic inputs + one review action, calls external proposer 0, returns `final_blocked`, and emits private-free 14-action history.
- [x] Add negative tests for navigation timeout/reject/wrong event/query/fragment, page drift, transient-empty then stable confirm, never-stable confirm, residual form controls on confirm, and final control drift. Review mutation occurs at most once.
- [x] Run Harness + TECH PLAY workflow, syntax, diff check, navigation-guard mutation proof, fresh Sol review.
- [x] Authenticated live E2E reaches exact confirm, exposes one safe final control, final click 0, private scalar projection leak 0, and closes only the owned page.
