# LM-33b Panel Read API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add five session-authenticated, read-only JSON endpoints for the Life Manager control panel with explicit no-data states and tenant isolation.

**Architecture:** A focused `panel-api.js` HTTP handler resolves the LM-33a cookie to a UID before dispatching endpoint-specific readers. Every PostgREST query is horizontally filtered by that server-derived UID; calendar reads receive it directly. Missing PHYSICAL and FINANCIAL sources remain explicit `no_data` rather than synthesized values.

**Tech Stack:** Node.js 20 CommonJS, `node:http`, `node:test`, existing calendar interpreter/transport, existing LM-33a session auth, existing LM-32 gate functions, Supabase PostgREST.

## Global Constraints

- Routes are exactly `GET /api/panel/timeline`, `/scores`, `/ledger`, `/gates`, and `/settings`.
- Every route requires the `lm_panel_session` cookie; no request-supplied UID is accepted.
- All endpoints are read-only JSON; non-GET methods return 405 and no write occurs.
- Data absence is represented honestly with `no_data: true`; no organ score is invented.
- No production or staging deployment occurs in this order.
- The local fixture smoke starts an HTTP server and calls all five endpoints.

---

### Task 1: Lock the authenticated HTTP contract in tests

**Files:**
- Modify: `apps/life-call/lib/panel-auth.test.js`
- Create: `apps/life-call/lib/panel-api.test.js`

**Interfaces:**
- Consumes: `handlePanelRequest(req, res, opts)` and its session cookie.
- Produces: wished-for `handlePanelApiRequest(req, res, opts)` behavior for five GET routes.

- [x] **Step 1: Write failing tests** for cookie scope `/`, five 200 JSON shapes, 401 without a session, 405 for writes, and session-UID tenant isolation.
- [x] **Step 2: Run `node --test lib/panel-auth.test.js lib/panel-api.test.js`** and confirm failures are caused by the missing API/cookie behavior.

### Task 2: Implement the minimal read model and wire it into life-call

**Files:**
- Create: `apps/life-call/lib/panel-api.js`
- Modify: `apps/life-call/lib/panel-auth.js`
- Modify: `apps/life-call/server.js`
- Modify: `apps/life-call/package.json`

**Interfaces:**
- Consumes: `sessionUid`, `cookieValue`, `interpretCalendarEvent`, `lockedDiscoveryGates`, and `DISCOVERY_STRINGS`.
- Produces: `handlePanelApiRequest(req, res, opts)` and JSON documents for timeline, scores, ledger, gates, and settings.

- [x] **Step 1: Change the session cookie to `Path=/`** so it reaches `/api/panel/*`.
- [x] **Step 2: Implement session-first routing and UID-filtered readers** with injected fetch/calendar/clock support for fixture tests.
- [x] **Step 3: Add `/api/panel/*` routing in `server.js`** and include the focused test in `npm test`.
- [x] **Step 4: Run the focused tests** and keep the implementation minimal until GREEN.

### Task 3: Add and execute the five-endpoint fixture smoke

**Files:**
- Create: `apps/life-call/scripts/smoke-panel-api-fixture.js`
- Modify: `apps/life-call/package.json`

**Interfaces:**
- Consumes: the production `handlePanelApiRequest` handler with a fixture PostgREST/calendar adapter.
- Produces: `npm run smoke:panel-api` exit 0 after all five authenticated HTTP calls return valid JSON.

- [x] **Step 1: Start a loopback HTTP server around the production handler** with two-tenant fixtures.
- [x] **Step 2: Call all five endpoints with one valid session cookie** and assert status, JSON shape, and no foreign UID leakage.
- [x] **Step 3: Run `npm run smoke:panel-api`** and confirm all five endpoints report 200 and exit 0.

### Task 4: Reconcile the SSOT and finish the branch

**Files:**
- Modify: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`

**Interfaces:**
- Consumes: fresh focused, smoke, and full-suite outputs.
- Produces: current order-8b status/evidence in the spec and a PR targeting `dev`.

- [x] **Step 1: Update the LM-33b row** with the implemented contract and local verification evidence; do not claim staging evidence.
- [x] **Step 2: Run `npm test` and `npm run smoke:panel-api` fresh** and inspect `git diff --check` plus the scoped diff.
- [x] **Step 3: Fetch, stage only order-8b paths, commit, push, and open a PR to `dev`.**
- [ ] **Step 4: Send the required agmsg DONE report** with actual test output, five endpoint results, commit, and PR URL.
