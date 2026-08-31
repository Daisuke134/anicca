# TECH PLAY Input and Confirm Inspector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development and test-driven-development to implement this plan task-by-task.

**Goal:** Convert the authenticated TECH PLAY input page into a bounded, privacy-safe control contract without clicking or filling anything.

**Architecture:** Extend only the existing production Browser Harness inspector. Add exact TECH PLAY candidate/event/ticket binding and a provider-specific DOM projection for `/event/join/<same event ID>`. The input projection validates the unique selected candidate ticket, required organizer-answer controls, known default-on opt-out controls, and review CTA. Confirm-page inspection is a separate next slice. This slice observes controls only; value resolution, action execution, final-effect polling, routing, evidence, and live state remain disabled.

**Tech Stack:** Node.js CommonJS, Playwright-compatible locators, `node:test`, existing `safeControl` and visibility semantics.

## Measured official contract

- Input URL exact `https://techplay.jp/event/join/999190`; selected ticket radio value `98036` occurs once.
- Answer inputs use exact names `enqueteAnswers[<positive question ID>]` and labels. Current required questions are `氏名`, `メールアドレス`, `年齢`, `キャリア状況`, `所属企業（学校）名`, and `職種`.
- Required markers are visible `*` in each question label; HTML `required` is not set.
- Default-on buttons use `role=checkbox`, `aria-checked=true`, and exact safe ID families `area_<ID>`, `tag_<ID>`, `organizer_<ID>`, plus `icon_published` and `use_as_preset`. Hidden companion inputs must never be duplicated as controls.
- Review CTA exact `同意して内容を確認する`; confirm URL exact `/event/join/<ID>/confirm`; final CTA exact `申し込みを確定する` and is one enabled `button[type=button]`.
- All owned temporary tabs returned 4→4; no final click or registration occurred.

## Global Constraints

- Luna owns exactly `apps/mr-bot/lib/connector-production-browser-harness.js` and `apps/mr-bot/lib/connector-production-browser-harness.test.js`. Other files are out of scope.
- Production target about 70–100 LOC; test target about 110–170 LOC. Confirm-page inspection is removed to keep the active item inside the production soft target.
- Strict TDD with focused RED caused only by absent TECH PLAY inspection.
- Candidate binding must be exact `techplay-event://event/<positive ID>`, `https://techplay.jp/event/<same ID>`, and positive-string `ticket_id`.
- Input page acceptance requires exact HTTPS host/path with no query/fragment/credentials/port, exact candidate event ID, exactly one selected non-answer radio matching candidate ticket ID, and no second ticket radio.
- Inspect at most 150 actionable nodes. Reuse ancestor-aware computed visibility; reject hidden/disconnected/disabled/zero-size controls, duplicate IDs/names, unlabeled required questions, ambiguous groups/options, unexpected checkbox ID families, duplicate review/final CTA, wrong button type, and page drift.
- Expose only safe control metadata: deterministic token, kind, public label/question, required/completed/submittable booleans. Never return entered values, selected private answers, email/name, csrf/auth/profile, DOM HTML, or ticket ID as a raw value field.
- Known checked opt-outs are represented once as incomplete required `ax_uncheck`-eligible controls; unchecked opt-outs are complete or omitted. The review CTA is submittable only when all required answer groups are complete and all known opt-outs are unchecked.
- Confirm page and `techplay_final_submit_<event ID>` are explicitly deferred to the next slice.
- No click/fill/navigation, resolver/profile read, direct action, provider workflow/factory/router/native order, evidence, Calendar, Telegram, schedule, or launchd mutation.

### Task 1: Add TECH PLAY input-page inspection only

**Files:**
- Modify: `apps/mr-bot/lib/connector-production-browser-harness.js`
- Modify: `apps/mr-bot/lib/connector-production-browser-harness.test.js`

- [x] Add failing real-DOM-shaped tests for empty/partially/fully completed input, seven default opt-outs, and exact ticket binding.
- [x] Add negative tests for wrong URL/event/ticket, duplicate ticket/CTA/ID/name, unknown checked checkbox, missing required marker/label, hidden/disabled/opacity/ancestor-hidden/zero-size controls, too many nodes, private-value non-exposure, and page drift.
- [x] Run the focused named tests; RED must be caused by TECH PLAY inspector absence.
- [x] Implement only exact binding and observation projection using existing visibility/safe-control patterns.
- [x] Run full Browser Harness tests, adjacent TECH PLAY workflow tests, syntax checks, and `git diff --check`.
- [x] Temporarily remove exact candidate ticket binding, prove its named negative test fails, restore it, and rerun GREEN.
- [x] Self-review and report RED/GREEN counts, mutation result, LOC, exact scope, and concerns without commit/push. Sol owns fresh review, SSOT, commit, and push.
