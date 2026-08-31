# TECH PLAY Parent Readback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development and test-driven-development to implement this plan task-by-task.

**Goal:** Prove TECH PLAY registration state from the authenticated official canonical event payload without treating the join or confirm form as success.

**Architecture:** Extend the existing isolated TECH PLAY workflow only. Reuse its exact canonical event/ticket binding and bounded main-document Inertia reader. `readProviderState` may navigate to the selected canonical event URL, then returns `registered` only when the same event has exactly the selected ticket and that ticket has `is_joined === true`; it returns `absent` only for the same currently actionable ticket with `is_joined === false`. Every identity, URL, ticket-count, ticket-ID, transport, redirect, malformed-state, or page-drift ambiguity returns `unavailable`. Direct action remains disabled until the Browser Harness slice.

**Tech Stack:** Node.js CommonJS, Playwright-compatible page adapter, `node:test`, existing TECH PLAY workflow helpers.

## Measured official contract

- Authenticated input page: `https://techplay.jp/event/join/999190` with one selected free ticket `98036` and six required organizer questions.
- The input CTA is exactly `同意して内容を確認する`; submitting it navigates to `https://techplay.jp/event/join/999190/confirm` and does not complete registration.
- Confirm page has exactly one enabled final CTA `申し込みを確定する`. It is a React `button[type=button]`; this slice does not click it.
- The canonical event payload binds event ID, `event_info_states`, and `attend_types[].id/is_joined` in one official response. The existing reader projects only those safe fields and excludes csrf/auth/profile.
- Shared-CDP inspection used one owned temporary page and restored page count 4→4. No application or final submission occurred.

## Global Constraints

- Luna owns exactly `apps/mr-bot/lib/connector-techplay-workflow.js` and `apps/mr-bot/lib/connector-techplay-workflow.test.js`. Other files are out of scope.
- Production target about 45–75 LOC; test target about 70–110 LOC. Browser controls, private values, final click, production routing, evidence, Calendar transport, schedule, and live state are explicitly removed.
- Strict TDD: add focused failing tests first; RED must show the current `unavailable` stub is insufficient. Implement minimum GREEN.
- Exact binding remains `techplay-event://event/<positive ID>`, `https://techplay.jp/event/<same ID>`, and candidate `ticket_id` positive string.
- `registered` requires the exact canonical response URL/status/current URL, exact event ID, exactly one ticket, exact candidate ticket ID, and `is_joined === true`.
- `absent` requires the same exact identity/ticket with `is_joined === false` plus the same visible native-open action state already required by discovery. Join and confirm URLs, redirects, missing page URL, duplicated/mismatched tickets, malformed joined state, transport error, unsafe/closed state, and pre/post read page drift are `unavailable`.
- Never return title, email, answers, auth state, csrf, profile, or ticket data in readback. Output is status only.
- Direct action remains `{status:"failed", safe_reason:"techplay_direct_requires_harness"}` and must not click.

### Task 1: Add strict canonical parent readback

**Files:**
- Modify: `apps/mr-bot/lib/connector-techplay-workflow.js`
- Modify: `apps/mr-bot/lib/connector-techplay-workflow.test.js`

- [x] Add failing tests for exact registered, exact absent, join/confirm not-success, wrong ticket/event/current/response URL, duplicate tickets, malformed `is_joined`, closed/hidden action, navigation/read failures, and pre/post page drift.
- [x] Run focused tests and record RED caused only by the current readback stub.
- [x] Implement the minimum readback using the existing bounded safe projection and exact candidate validation.
- [x] Run focused plus adjacent Eventbrite/Doorkeeper tests, both-file syntax checks, and `git diff --check`.
- [x] Temporarily remove the exact ticket-ID guard, prove its named negative test fails, restore it, and rerun GREEN.
- [x] Self-review and report RED/GREEN counts, mutation result, LOC, exact scope, and concerns without commit/push. Sol owns fresh review, SSOT, commit, and push.
