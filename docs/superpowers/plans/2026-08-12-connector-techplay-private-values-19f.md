# TECH PLAY Private Value Resolver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development and test-driven-development to implement this plan task-by-task.

**Goal:** Resolve the six inspected TECH PLAY organizer answers entirely in the parent process from existing private SSOTs, without exposing values to the model or DOM inspector.

**Architecture:** Extend only `createPrivateValueResolver`. The existing private identity profile supplies Japanese legal name and account email. The mode-0600 form profile supplies date of birth and exact organizer answers. Add a strict injected clock to compute age in Asia/Tokyo. Radio controls resolve to boolean true only when their public option exactly matches the private answer for the same public question. This slice does not operate DOM controls.

**Tech Stack:** Node.js CommonJS, existing private profile readers, `node:test`, `Intl.DateTimeFormat`.

## Global Constraints

- Luna owns exactly `apps/mr-bot/lib/connector-production-browser-harness.js` and matching test. Other files are out of scope.
- Production target about 25–45 LOC; test target about 70–110 LOC.
- Strict TDD; all existing providers and resolver behavior remain unchanged.
- TECH PLAY resolution accepts only incomplete required, non-submittable controls whose token matches the shipped `techplay_answer_*` grammar.
- Scalar exact mapping: `氏名` → private `name_kanji`; `メールアドレス` → private `email`; `年齢` → age derived from exact ISO `YYYY-MM-DD` DOB; `所属企業（学校）名` → exact form answer key.
- DOB accepts `生年月日` and/or `Date of Birth` only when present values are exact equal valid dates. Compute integer age at current Asia/Tokyo calendar date; require 18–100. Reject future/invalid/mismatched/missing DOB, invalid/throwing clock, whitespace/control chars, oversized value, and wrong control kind/token/state.
- Radio exact mapping uses `question` + option label against the form profile. Only one option should resolve `true` for each question; every nonmatching/cross-question option returns null.
- Reject ticket, opt-out, review/final controls and unknown scalar labels. Do not read a private profile for rejected control shapes.
- Never include private values in observations, runner prompt, errors, audit, logs, state, tests, or return objects beyond the scalar/boolean value returned directly to the parent action operator.
- No private file mutation in this code slice. After ship, Sol may update the existing mode-0600 form profile with exact current non-secret answer keys; that state update is not committed.
- No DOM inspect/operate, click/fill, action proposer, workflow/factory/router/native/evidence/Calendar/schedule/live-state changes.

### Task 1: Add exact TECH PLAY parent-only values

**Files:**
- Modify: `apps/mr-bot/lib/connector-production-browser-harness.js`
- Modify: `apps/mr-bot/lib/connector-production-browser-harness.test.js`

- [x] Add RED tests for all four scalar mappings, two exact radio choices, wrong/cross question, malformed controls, DOB and clock boundaries, private-reader nonaccess on rejection, and no private output in inspection/runner paths.
- [x] Implement the minimum provider-specific resolver before the generic provider-neutral branch.
- [x] Run full Browser Harness and TECH PLAY workflow tests, syntax checks, and `git diff --check`.
- [x] Temporarily remove exact radio question binding or DOB equality guard, prove its named negative fails, restore it, and rerun GREEN.
- [x] Self-review and report evidence without commit/push. Sol owns fresh review, SSOT, commit, and push.
