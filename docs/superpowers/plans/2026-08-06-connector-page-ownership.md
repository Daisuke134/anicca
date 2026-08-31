# Connector Page Ownership Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Connector's prose-only tab receipt and repeated browser discovery with a parent-owned, page-scoped, durable browser transaction on Connector's existing CloakBrowser `:9222`.

**Architecture:** A Connector-only target lease owns one default-context target from creation through parent readback and cleanup. The agent receives only a fenced page capability; it cannot enumerate tabs, attach to the browser endpoint, or close the browser. The parent retains the operation lock, probes renderer liveness, verifies the provider effect, captures evidence, then releases the target.

**Tech Stack:** Node.js, `node:test`, `playwright-core`, Chrome DevTools Protocol, mode-0600 JSON state.

## Global Constraints

- Gig repository, launchd, browser, profile, state, lock, vault, and `:9223` are read-only and must never be imported or mutated.
- Connector owns only `http://127.0.0.1:9222` and Connector state beneath its configured evidence/state directories.
- No raw page body, cookie, token, OTP, private profile value, form answer, or raw prompt may enter ownership state or evidence.
- Every behavior change follows Superpowers RED → GREEN and fresh verification before commit.
- Agent self-report is never an external-effect oracle; the parent must read the same target independently.

---

### Task 1: Durable Connector Target Lease

**Files:**
- Create: `apps/mr-bot/lib/connector-target-lease.js`
- Create: `apps/mr-bot/lib/connector-target-lease.test.js`
- Modify: `apps/mr-bot/lib/connector-tab-owner.js`
- Modify: `apps/mr-bot/lib/connector-tab-owner.test.js`

**Interfaces:**
- Consumes: Connector-owned absolute ledger directory, target ID, direct page WebSocket, canonical Luma URL.
- Produces: `createConnectorTargetLease(options)` with `claim(input)`, `heartbeat(fence)`, `probe(fence)`, and `release(fence)`; fence fields are `owner_token`, `generation`, and `target_id`.

- [x] **Step 1: Write the failing lease tests**

  Add real filesystem tests proving: mode-0600 atomic claim; a second owner cannot claim the target; wrong token/generation cannot heartbeat or release; `probe()` returns false for an unresponsive renderer; stale rows are reaped only after their operation lock is acquired; release removes only the fenced Connector target.

- [x] **Step 2: Run the focused test and verify RED**

  Run: `cd apps/mr-bot && node --test lib/connector-target-lease.test.js`

  Expected: FAIL because `connector-target-lease.js` does not exist.

- [x] **Step 3: Implement the minimal lease**

  Use an atomic JSON ledger guarded by a filesystem lock, schema version 1, random owner token, monotonic generation, heartbeat timestamp, direct `ws://127.0.0.1:9222/devtools/page/<target>` validation, and injected `probeTarget`/`closeTarget` functions. Do not copy or import Gig files.

- [x] **Step 4: Connect tab-owner receipt generation to the lease**

  `connector-tab-owner.claim()` must claim the uniquely observed target through `targetLease.claim()` and return the lease fence in its private receipt. The receipt must not be considered ownership if durable claim fails.

- [x] **Step 5: Run focused tests and verify GREEN**

  Run: `cd apps/mr-bot && node --test lib/connector-target-lease.test.js lib/connector-tab-owner.test.js`

  Expected: all tests pass with zero failures.

- [ ] **Step 6: Commit Task 1**

  Commit message: `feat(connector): add durable target lease`

### Task 2: Parent-Created Default-Context Target

**Files:**
- Create: `apps/mr-bot/lib/connector-browser-target-controller.js`
- Create: `apps/mr-bot/lib/connector-browser-target-controller.test.js`
- Modify: `apps/mr-bot/lib/cloakbrowser-daily-driver.js`
- Modify: `apps/mr-bot/lib/cloakbrowser-daily-driver.test.js`
- Modify: `apps/mr-bot/lib/connector-tab-owner.js`
- Modify: `apps/mr-bot/lib/connector-tab-owner.test.js`
- Modify: `apps/mr-bot/lib/connector-native-runtime.js`
- Modify: `apps/mr-bot/lib/connector-native-runtime.test.js`

**Interfaces:**
- Consumes: `browser.newBrowserCDPSession()`, `Target.createTarget`, Task 1 lease.
- Produces: `withLumaPage()` metadata containing one fenced `page_websocket`; parent retains the Playwright page and release callback.

- [x] **Step 1: Write failing tests** proving the parent calls `Target.createTarget` once, claims before navigation actions are delegated, never uses `context.newPage()`, and releases in `finally` after parent readback.
- [x] **Step 2: Run focused tests and verify RED:** `cd apps/mr-bot && node --test lib/cloakbrowser-daily-driver.test.js lib/connector-native-runtime.test.js`.
- [x] **Step 3: Implement the minimal parent target lifecycle** using the default authenticated context, one browser CDP session, bounded target-to-page binding, heartbeat, renderer probe, and parent-only close/release.
- [x] **Step 4: Run focused tests and verify GREEN** with the same command.
- [x] **Step 5: Commit Task 2** with `feat(connector): own browser target lifecycle` (`1f04a2341`).

### Task 3: Model-Only Form Decisions and Parent-Owned Browser Oracle

**Files:**
- Modify: `apps/mr-bot/lib/connector-agentic-registration.js`
- Modify: `apps/mr-bot/lib/connector-agentic-registration.test.js`
- Modify: `apps/mr-bot/lib/luma-form-answer-policy.js`
- Modify: `apps/mr-bot/lib/luma-form-answer-policy.test.js`
- Modify: `apps/mr-bot/lib/luma-browser-provider.js`
- Modify: `apps/mr-bot/lib/luma-browser-provider.test.js`
- Modify: `apps/mr-bot/lib/connector-native-runtime.js`

**Interfaces:**
- Consumes: the form schema observed by the Task 2 parent-owned page and the private profile for one action.
- Produces: one bounded Terra decision containing answers only. Terra receives no browser endpoint, page WebSocket, target inventory, browser tool, or close capability.
- The parent-owned Playwright page remains the only browser executor and performs real locator actions, provider readback, screenshot, and fenced cleanup on the same target.

- [x] **Step 1: Write failing tests** proving Terra receives only a sanitized form schema and profile. The prompt contains no endpoint, page WebSocket, target receipt, tab enumeration, inline Node/Playwright bootstrap, `connectOverCDP`, or `browser.close`. Require exactly one Terra invocation and a complete validated answer plan.
- [x] **Step 2: Run focused tests and verify RED:** `cd apps/mr-bot && node --test lib/connector-agentic-registration.test.js lib/luma-form-answer-policy.test.js lib/luma-browser-provider.test.js` (旧境界で2件RED)。
- [x] **Step 3: Implement the minimal model-decision adapter.** Deterministic profile answers stay local; only unresolved ordinary questions are sent once to Terra. Reject secret-shaped fields, OTP/password/file controls, invalid options, unknown keys, duplicates, and incomplete required answers.
- [x] **Step 4: Keep the entire effect in the parent.** The existing owned page opens the form, reads its schema, merges validated Terra decisions, fills using user-facing Playwright actions, clicks final submit once, then performs independent provider readback and PNG capture before fenced cleanup.
- [x] **Step 5: Run focused tests and the Connector suite:** focused 17/17、pretest 12/12、outbound 336/336 GREEN。
- [ ] **Step 6: Run the existing Connector launchd live acceptance** and require one trace with one target, one agent session, zero agent closes, real submit, parent marker readback, PNG SHA, and parent release. Do not touch Gig or `:9223`.
- Run 178 observation: schedule-owned lifecycle and parent cleanup were healthy, but no new form submit occurred; two existing-effect readbacks produced PNG evidence and then stopped at ticket evidence, while two candidates were unavailable. This is not Step 6 completion.
- Run 180 observation: fresh inventory 27 → Calendar eligible 4 → spend ordered 2; both attempts were `LUMA_RSVP_UNAVAILABLE`, no Terra child/evidence and no delivery increment. Step 6 remains open because no submit-capable candidate existed.
- [ ] **Step 7: Update the master spec with measured evidence and commit** using `feat(connector): complete page-scoped registration transaction`.

### Task 4: Keep Optional Ticket Enrichment Out of the Core Delivery Gate

**Files:**
- Modify: `apps/mr-bot/lib/connector-native-write-pipeline.js`
- Modify: `apps/mr-bot/lib/connector-native-write-pipeline.test.js`

**Interfaces:**
- Consumes: verified provider marker/PNG receipt plus optional confirmation-mail and ticket-QR services.
- Produces: Calendar, coverage, and registration-page Telegram delivery from the core receipt even when optional mail/QR enrichment is unavailable. A verified ticket is delivered additionally when present.

- [x] **Step 1: Write a failing regression test** reproducing run 178: confirmation/QR failure after a verified RSVP must still call Calendar, coverage rebuild, message build, and registration-page Telegram delivery; it must not claim ticket delivery.
- [x] **Step 2: Run the focused test and verify RED:**旧codeで1件RED。
- [x] **Step 3: Implement the smallest state-machine change.** Capture ticket enrichment failure as a bounded optional status, continue the core chain, and attempt ticket Telegram only when a verified ticket artifact exists. Ticket Telegram failure also remains optional and observable.
- [x] **Step 4: Run focused, pretest, and full outbound suites.** focused 21/21、pretest 12/12、outbound 337/337 GREEN。
- [x] **Step 5: Commit/push, then let the existing Connector launchd prove Calendar and registration-page Telegram receipt on the next verified registration readback.** run 179でdelivery 2→3、PNG SHA、Calendar ref、Telegram card `7864` / photo `7865`を同一lineageでlive確認。Gig/`:9223`は未変更。
