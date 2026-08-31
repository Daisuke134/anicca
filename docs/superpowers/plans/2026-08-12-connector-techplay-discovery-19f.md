# TECH PLAY Discovery Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development and test-driven-development to implement this plan task-by-task.

**Goal:** Discover current, free, in-person Tokyo TECH PLAY events through official RSS/detail pages and reject unsafe rows before any action.

**Architecture:** Add one isolated script-first workflow. The default source navigates the official 50-item TECH PLAY RSS feed, extracts exact canonical event URLs, then reads the public Inertia detail payload from each canonical page. Reuse the existing 14-day Asia/Tokyo window, canonical identity, Calendar overlap/idempotent-coverage semantics, aggregate audit callback, and fail-closed stage errors. Direct action/readback and production routing stay outside this slice.

**Tech Stack:** Node.js CommonJS, Playwright-compatible page adapter, `node:test`, existing `zonedSlotInstant` and SHA-256 helpers.

## Evidence and reuse

- TECH PLAY official event index, <https://techplay.jp/event>: 「開催予定463件/開催中27件/全490件」を公開し、canonical detail pathは`/event/<numeric ID>`。
- TECH PLAY official RSS, <https://rss.techplay.jp/event/w3c-rss-format/rss.xml>: 「点在している技術勉強会、セミナー情報をまとめて掲載」と説明し、current 50 canonical detail URLsを返す。
- TECH PLAY official detail example, <https://techplay.jp/event/999180>: public detail payloadがTokyo address、Unix start/end、native action state、free ticket ID/fee/capacityを同じevent identityへ束縛する。
- GitHub code search found multiple consumers of the official RSS URL, but none satisfying this Connector's identity/free/Calendar/action-safety contract. Reuse the official RSS transport; do not copy an unrelated crawler.

## Global Constraints

- Luna owns exactly `apps/mr-bot/lib/connector-techplay-workflow.js` and `apps/mr-bot/lib/connector-techplay-workflow.test.js`. Other files are out of scope.
- Production target about 160–220 LOC; test target about 180–260 LOC. The provider boundary exceeds the 100 LOC soft target, so action, readback, evidence, Calendar transport, router, harness, native order, and launchd changes are explicitly removed.
- Strict TDD: tests first, focused RED caused by the missing workflow, then minimum GREEN implementation.
- Exact identity: `techplay-event://event/<positive integer>` and `https://techplay.jp/event/<same ID>` only. Reject query, fragment, trailing slash, credentials, port, uppercase raw host, alternate/subdomain hosts, mismatched payload ID/current URL, duplicate IDs, and more than 50 RSS rows.
- Eligibility requires native TECH PLAY action (`event_url` null in event and button state), `offline_only`, Tokyo in address/place, valid increasing start/end inside `[today 00:00 JST, day+14 00:00 JST)`, open visible `apply` state, not ended, no explicit elementary/junior-high/high-school-only audience marker in title/description, and exactly one available free ticket with positive ticket ID/capacity, finite nonnegative entered count, `entrance_fee === 0`, `is_full === false`, `is_joined === false`, and no Stripe payment.
- If recruitment start/end exists, `now` must be within the half-open interval. Paid, mixed/online, external-link, closed/full/joined, malformed, or ambiguous multi-free-ticket detail is skipped. Identity mismatch and transport/contract failures throw provider-specific safe errors.
- Preserve existing Calendar rules: timed overlap blocks unless its `connector_idempotency` equals SHA-256 of the same canonical URL.
- Audit only aggregate counts: `discovered_count`, `within_window_count`, `eligible_count`, `calendar_free_count`, `selected_count`. No title, URL, ticket ID, identity, body, or profile.
- No browser click, form, login/OAuth, external write, Calendar write, screenshot, Telegram, Connector state, schedule, or launchd mutation.

### Task 1: Add strict TECH PLAY read-only discovery

**Files:**
- Create: `apps/mr-bot/lib/connector-techplay-workflow.js`
- Create: `apps/mr-bot/lib/connector-techplay-workflow.test.js`

- [x] Write failing tests for happy discovery, exact-coverage ordering, identity rejection, paid/external/online/closed/full/ambiguous/explicit school-age-only row skipping, timed Calendar conflict, aggregate audit, bounded dedup, and stage errors. Verify direct action fails safely and readback stays unavailable.
- [x] Run `node --test apps/mr-bot/lib/connector-techplay-workflow.test.js`; RED must be caused by the missing workflow/factory.
- [x] Export `createTechPlayDiscoveryWorkflow(options)` with only the minimum default RSS/detail readers and normalization described above.
- [x] Run focused tests, adjacent Eventbrite/Doorkeeper tests, `node --check`, and `git diff --check`.
- [x] Temporarily remove one canonical raw-equality or unique-free-ticket guard, prove its named negative test fails, restore it, and rerun GREEN.
- [x] Self-review and report RED/GREEN counts, mutation result, LOC, exact scope, and concerns without commit/push. Sol owns review, SSOT, commit, and push.
