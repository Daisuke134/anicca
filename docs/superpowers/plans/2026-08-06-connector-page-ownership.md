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
- Create: `apps/life-manager/lib/connector-target-lease.js`
- Create: `apps/life-manager/lib/connector-target-lease.test.js`
- Modify: `apps/life-manager/lib/connector-tab-owner.js`
- Modify: `apps/life-manager/lib/connector-tab-owner.test.js`

**Interfaces:**
- Consumes: Connector-owned absolute ledger directory, target ID, direct page WebSocket, canonical Luma URL.
- Produces: `createConnectorTargetLease(options)` with `claim(input)`, `heartbeat(fence)`, `probe(fence)`, and `release(fence)`; fence fields are `owner_token`, `generation`, and `target_id`.

- [x] **Step 1: Write the failing lease tests**

  Add real filesystem tests proving: mode-0600 atomic claim; a second owner cannot claim the target; wrong token/generation cannot heartbeat or release; `probe()` returns false for an unresponsive renderer; stale rows are reaped only after their operation lock is acquired; release removes only the fenced Connector target.

- [x] **Step 2: Run the focused test and verify RED**

  Run: `cd apps/life-manager && node --test lib/connector-target-lease.test.js`

  Expected: FAIL because `connector-target-lease.js` does not exist.

- [x] **Step 3: Implement the minimal lease**

  Use an atomic JSON ledger guarded by a filesystem lock, schema version 1, random owner token, monotonic generation, heartbeat timestamp, direct `ws://127.0.0.1:9222/devtools/page/<target>` validation, and injected `probeTarget`/`closeTarget` functions. Do not copy or import Gig files.

- [x] **Step 4: Connect tab-owner receipt generation to the lease**

  `connector-tab-owner.claim()` must claim the uniquely observed target through `targetLease.claim()` and return the lease fence in its private receipt. The receipt must not be considered ownership if durable claim fails.

- [x] **Step 5: Run focused tests and verify GREEN**

  Run: `cd apps/life-manager && node --test lib/connector-target-lease.test.js lib/connector-tab-owner.test.js`

  Expected: all tests pass with zero failures.

- [ ] **Step 6: Commit Task 1**

  Commit message: `feat(connector): add durable target lease`

### Task 2: Parent-Created Default-Context Target

**Files:**
- Create: `apps/life-manager/lib/connector-browser-target-controller.js`
- Create: `apps/life-manager/lib/connector-browser-target-controller.test.js`
- Modify: `apps/life-manager/lib/cloakbrowser-daily-driver.js`
- Modify: `apps/life-manager/lib/cloakbrowser-daily-driver.test.js`
- Modify: `apps/life-manager/lib/connector-tab-owner.js`
- Modify: `apps/life-manager/lib/connector-tab-owner.test.js`
- Modify: `apps/life-manager/lib/connector-native-runtime.js`
- Modify: `apps/life-manager/lib/connector-native-runtime.test.js`

**Interfaces:**
- Consumes: `browser.newBrowserCDPSession()`, `Target.createTarget`, Task 1 lease.
- Produces: `withLumaPage()` metadata containing one fenced `page_websocket`; parent retains the Playwright page and release callback.

- [ ] **Step 1: Write failing tests** proving the parent calls `Target.createTarget` once, claims before navigation actions are delegated, never uses `context.newPage()`, and releases in `finally` after parent readback.
- [ ] **Step 2: Run focused tests and verify RED:** `cd apps/life-manager && node --test lib/cloakbrowser-daily-driver.test.js lib/connector-native-runtime.test.js`.
- [ ] **Step 3: Implement the minimal parent target lifecycle** using the default authenticated context, one browser CDP session, bounded target-to-page binding, heartbeat, renderer probe, and parent-only close/release.
- [ ] **Step 4: Run focused tests and verify GREEN** with the same command.
- [ ] **Step 5: Commit Task 2** with `feat(connector): own browser target lifecycle`.

### Task 3: Fenced Single-Page Agent Capability and Parent Oracle

**Files:**
- Create: `apps/life-manager/lib/connector-page-session.js`
- Create: `apps/life-manager/lib/connector-page-session.test.js`
- Modify: `apps/life-manager/lib/connector-agentic-registration.js`
- Modify: `apps/life-manager/lib/connector-agentic-registration.test.js`
- Modify: `apps/life-manager/lib/luma-browser-provider.js`
- Modify: `apps/life-manager/lib/luma-browser-provider.test.js`

**Interfaces:**
- Consumes: Task 2 fenced direct page WebSocket and private profile for one action.
- Produces: a bounded page capability exposing snapshot, user-facing click/fill/check/select/press, settle, and screenshot; no browser endpoint, page inventory, raw DOM mutation, or close method.

- [ ] **Step 1: Write failing tests** proving the agent input contains no `receipt.endpoint`, `connectOverCDP`, page enumeration, inline Node instructions, or `browser.close`; all actions remain fenced to one target/generation.
- [ ] **Step 2: Run focused tests and verify RED:** `cd apps/life-manager && node --test lib/connector-page-session.test.js lib/connector-agentic-registration.test.js lib/luma-browser-provider.test.js`.
- [ ] **Step 3: Implement the minimal single-page capability** and bind it to one Terra turn. Reject fence mismatch, renderer death, navigation outside allowed registration origins, and any action after parent cancellation.
- [ ] **Step 4: Implement the parent oracle:** after agent return, reload/read the same target, require an exact registered or pending-approval marker, capture PNG, then close/release in the parent.
- [ ] **Step 5: Run focused tests and the Connector suite:** `cd apps/life-manager && node --test lib/connector-page-session.test.js lib/connector-agentic-registration.test.js lib/luma-browser-provider.test.js && npm run pretest:outbound && npm run test:outbound`.
- [ ] **Step 6: Run the existing Connector launchd live acceptance** and require one trace with one target, one agent session, zero agent closes, real submit, parent marker readback, PNG SHA, and parent release. Do not touch Gig or `:9223`.
- [ ] **Step 7: Update the master spec with measured evidence and commit** using `feat(connector): complete page-scoped registration transaction`.
