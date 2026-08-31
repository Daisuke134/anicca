# TECH PLAY Confirm Inspector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development and test-driven-development to implement this plan task-by-task.

**Goal:** Expose the unique final TECH PLAY registration control only on the exact same-event confirmation page, without clicking it.

**Architecture:** Extend only the shipped TECH PLAY Browser Harness inspector. The existing candidate binding selects input versus confirm by exact current URL. The confirm projection accepts one visible enabled `button[type=button]` with exact label `申し込みを確定する`, rejects any answer/opt-out/ticket controls or competing exact-label control, and returns one status-only safe control token. Action execution and final-effect polling remain a later slice.

**Tech Stack:** Node.js CommonJS, Playwright-compatible locator projection, `node:test`, existing TECH PLAY binding and visibility helpers.

## Measured official contract

- Submitting the non-final input CTA navigates from `/event/join/999190` to exact `https://techplay.jp/event/join/999190/confirm`.
- Confirm title is `イベント申込み確認 - TECH PLAY` and the final CTA occurs exactly once as enabled `BUTTON type=button` with text `申し込みを確定する`.
- Final button is React-operated and has no enclosing HTML form action. No final click occurred.
- Confirm inspection may be live-verified by filling the temporary input page from private SSOT, disabling all known opt-outs, clicking only the review CTA, inspecting, then closing the owned tab. This setup transition is not registration acceptance.

## Global Constraints

- Luna owns exactly `apps/mr-bot/lib/connector-production-browser-harness.js` and matching test. Other files are out of scope.
- Production target about 20–40 LOC; test target about 60–100 LOC.
- Strict TDD. Existing input inspector and all provider behavior must remain unchanged.
- Require exact candidate `techplay-event://event/<ID>`, canonical `https://techplay.jp/event/<same ID>`, positive-string ticket ID, and current `https://techplay.jp/event/join/<same ID>/confirm` with no query/fragment/credentials/port.
- At most 150 actionable nodes. Reuse ancestor/computed visibility and global-ID uniqueness.
- Confirm must contain no `enqueteAnswers[...]`, non-answer ticket radio, role checkbox, or visible native checkbox. Exact final-label control count is one, tag/type is `BUTTON`/`button`, enabled, visible, connected, nonzero, and aria-enabled.
- Return exactly `{control:techplay_final_<event ID>, kind:button, label:申し込みを確定する, required:false, completed:false, submittable:true}`. Never return page text, input values, ticket value, identity, auth/csrf/profile, or private answers.
- Wrong event/path, input page, duplicate/wrong-type/hidden final, extra actionable registration controls, duplicate IDs, page drift, or oversized set returns no controls.
- No click/fill/navigation in production, no action resolver/operation, no workflow/factory/router/native/evidence/Calendar/schedule/live-state changes.

### Task 1: Add exact confirm-page inspection

**Files:**
- Modify: `apps/mr-bot/lib/connector-production-browser-harness.js`
- Modify: `apps/mr-bot/lib/connector-production-browser-harness.test.js`

- [x] Add RED tests for exact confirm success and wrong URL/event, duplicate/wrong-type/hidden/disabled/ancestor-hidden/opacity/zero-size final, residual answer/ticket/checkbox, duplicate ID, page drift, 151 nodes, and privacy-safe output.
- [x] Implement the minimum confirm projection reusing the shipped TECH PLAY visibility logic.
- [x] Run full Browser Harness and TECH PLAY workflow tests, syntax checks, and `git diff --check`.
- [x] Temporarily remove exact confirm event-ID binding, prove its named negative fails, restore it, and rerun GREEN.
- [x] Live inspect one owned temporary confirm page without final click; prove one safe control and page cleanup.
- [x] Self-review and report evidence without commit/push. Sol owns fresh review, SSOT, commit, and push.
