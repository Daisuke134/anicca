# Mr.bot Mobile v1 Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose a tenant-safe `/api/mobile/v1` adapter for native onboarding, direct analysis, semantic chat, questions, calls, devices, and account deletion without creating a second Mr.bot engine.

**Architecture:** One raw-HTTP router authenticates a rotating bearer session and passes a server-derived scope into small domain adapters. A Supabase store applies `scope.uid` to every query. Semantic outbox rows hold message keys and arguments; projection localizes at read time. Direct analysis reuses Calendar/event/route modules but never the paid-plus-phone scheduler cohort. Contract JSON in `apps/mr-bot/contracts/mobile-v1/` is the shared decoder boundary for Node and Swift.

**Tech Stack:** Node.js 20 CommonJS, `node:test`, Zod, Supabase Auth/PostgreSQL, Composio Calendar, existing travel/transit/call transports.

## Global Constraints

- Mount exactly one router under `/api/mobile/v1`; do not add endpoint conditionals throughout `server.js`.
- Do not accept `uid` as authority in path, query, header, or body.
- Every mutation requires `Idempotency-Key`; same key/body replays the result, same key/different body returns 409 with zero side effects.
- Refresh tokens rotate by family; reusing an old refresh token revokes the family.
- The router and every imported module must have no location/late/recipient/approval/attendee-send symbol or route.
- `product_locale` and `call_language` are independent. Calls default off.

## File Structure

| File | Responsibility |
|---|---|
| `apps/mr-bot/contracts/mobile-v1/*.json` | Frozen success/error fixtures shared with Swift tests |
| `apps/mr-bot/lib/mobile-v1-router.js` | HTTP dispatch, JSON/error envelope, auth/idempotency entry |
| `apps/mr-bot/lib/mobile-session.js` | OAuth state, exchange, bearer validation, refresh/revoke |
| `apps/mr-bot/lib/mobile-idempotency.js` | Payload hash and durable result replay |
| `apps/mr-bot/lib/mobile-store.js` | Tenant-scoped Supabase operations |
| `apps/mr-bot/lib/mobile-bootstrap.js` | Bootstrap projection |
| `apps/mr-bot/lib/mobile-profile.js` | Allowlisted profile validation/update |
| `apps/mr-bot/lib/mobile-analysis.js` | Direct next-event state machine |
| `apps/mr-bot/lib/mobile-route.js` | Event anchor and mobile route projection |
| `apps/mr-bot/lib/mobile-outbox.js` | Semantic append, cursor read, locale projection |
| `apps/mr-bot/lib/mobile-localization.js` | en/ja semantic messages and script guards |
| `apps/mr-bot/lib/mobile-question.js` | Tenant-bound open-question consume/reply |
| `apps/mr-bot/lib/mobile-call.js` | Confirmed call gate and durable limits |
| `apps/mr-bot/lib/mobile-device.js` | APNs device upsert/delete |
| `apps/mr-bot/lib/mobile-account.js` | Confirmed account deletion and receipt |
| `apps/mr-bot/migrations/2026-08-08-lm-mobile-v1.sql` | Profile fields, sessions, idempotency, outbox, devices, deletion RPCs |
| `apps/mr-bot/server.js` | One import and one `/api/mobile/v1` mount |

### Task 1: Freeze Contracts and Database Invariants

**Files:**
- Create: `apps/mr-bot/contracts/mobile-v1/bootstrap.json`
- Create: `apps/mr-bot/contracts/mobile-v1/analysis-*.json`
- Create: `apps/mr-bot/contracts/mobile-v1/chat-page.json`
- Create: `apps/mr-bot/contracts/mobile-v1/error.json`
- Create: `apps/mr-bot/migrations/2026-08-08-lm-mobile-v1.sql`
- Test: `apps/mr-bot/test/mobile-profile-contract.test.js`

- [ ] Encode the approved spec's bootstrap, five terminal analysis states, localized chat, route, question, call receipt, device receipt, deletion receipt, and structured error as JSON fixtures with ISO-8601 instants and nullable provider facts.
- [ ] Write tests that parse every fixture and reject extra authority fields such as client `uid`.
- [ ] Add `product_locale` default `en`, explicit `calls_enabled=false`, and nullable `call_language`/phone profile fields.
- [ ] Add mobile OAuth state, access-session hash, rotating refresh family, idempotency receipt, semantic outbox with monotonic sequence, APNs device, durable call-attempt, and deletion-receipt tables.
- [ ] Add atomic functions for one-use OAuth claim, refresh rotation, idempotency claim/complete, cursor page, call limit claim, and authenticated account deletion.
- [ ] Run fixture/migration tests; record RED before schema creation and GREEN afterward.
- [ ] Apply to staging and read each table/function signature back; commit and push Gate 2 fixtures before iOS decoding work begins.

### Task 2: Implement Mobile Session Ownership

**Interface:**

```javascript
async function startCalendarSession(input, deps)
async function exchangeMobileSession(input, deps)
async function authenticateMobileRequest(req, deps) // -> { uid, sessionId, productLocale }
async function refreshMobileSession(refreshToken, deps)
async function revokeMobileSession(scope, deps)
```

- [ ] Write `mobile-calendar-session-contract.test.js` for invalid, expired, replayed, and wrong-owner state; all produce zero sessions.
- [ ] Add refresh tests for rotation, concurrent replay, family revocation, expiry, and logout revocation.
- [ ] Validate the Supabase/Google identity through Supabase `/auth/v1/user`; derive the Mr.bot UID server-side using the existing landing precedent.
- [ ] Reuse Composio OAuth ownership patterns, but issue mobile bearer tokens rather than panel cookies.
- [ ] Hash stored tokens and compare constant-time; never log raw codes or tokens.
- [ ] Run session tests and commit/push.

### Task 3: Enforce Tenant Scope and Idempotency

**Interface:**

```javascript
function createSupabaseMobileStore({ supaUrl, supaKey, fetchImpl })
async function withMobileIdempotency({ scope, key, payload, operation }, deps)
```

- [ ] Write `mobile-tenant-isolation.test.js` across profile, messages, route, question, call, device, and deletion operations.
- [ ] Write duplicate same-payload and conflicting-payload cases for every mutation.
- [ ] Make every store method accept `scope` first and internally add `uid=eq.<scope.uid>`; no public method accepts an arbitrary UID.
- [ ] Implement SHA-256 canonical payload hashing and atomic receipt replay modeled on the existing panel command store.
- [ ] Mutation-check one removed UID predicate and confirm the isolation test fails.
- [ ] Run isolation/idempotency tests and commit/push.

### Task 4: Bootstrap, Profile, and Direct Analysis

**Interfaces:**

```javascript
async function readMobileBootstrap(scope, deps)
function validateMobileProfilePatch(body)
async function patchMobileProfile(scope, patch, deps)
async function analyzeNextEvent(scope, input, deps)
```

- [ ] Write `mobile-phone-null-contract.test.js` proving `phone=null`, `paid=false` reaches real Calendar analysis and chat.
- [ ] Write `mobile-analysis-terminal-state.test.js` for exactly `route_ready`, `needs_information`, `no_upcoming_event`, `route_unavailable`, and `failed`.
- [ ] Require Calendar, name, home, and product locale; never require phone or paid state.
- [ ] Report real phases `reading_events`, `checking_locations`, `calculating_route` from stored analysis state, not timers.
- [ ] Reuse `fetchUpcomingEvents`/Calendar transport directly and bypass scheduler cohort selection.
- [ ] Append exactly one semantic terminal outbox message per idempotent analysis.
- [ ] Run profile/phone/analysis tests and commit/push.

### Task 5: Project Event-Anchored Routes

**Interfaces:**

```javascript
function buildAnchoredRouteRequest({ event, origin, direction })
async function computeMobileRoute(scope, event, origin, deps)
function projectMobileRoute(route, locale)
```

- [ ] Write `mobile-route-anchor`, `mobile-route-projection`, and `mobile-route-honesty` tests.
- [ ] Assert event date, event timezone, arrive-by outbound, depart-at return, day crossing, and DST-safe ISO/IANA representation.
- [ ] Preserve access/egress walk, service, headsign, platform, fare, transfers, geometry, provider attribution, and freshness when present.
- [ ] Represent unavailable facts as null and omit entrance, exit, optimal car, and crowding keys entirely.
- [ ] Use Gate 1 structured route and persistent cache; do not recalculate in the projection.
- [ ] Return one concrete localized unavailable reason when a route cannot be produced.
- [ ] Run route tests and commit/push.

### Task 6: Add Semantic Outbox and Stable Cursor

**Interfaces:**

```javascript
async function appendMobileMessage(scope, { type, key, args, userContent, route }, deps)
async function listMobileMessages(scope, cursor, deps)
function projectMobileMessage(row, locale)
```

- [ ] Write `mobile-chat-cursor.test.js` for monotonic pages, stable IDs, launch/foreground/APNs refetch, and no duplicates.
- [ ] Store message key plus structured arguments, never final generated prose as the only source.
- [ ] Keep Calendar title/location under `userContent`; route/provider names come from localized provider projection.
- [ ] Make cursor an opaque encoding of immutable sequence; invalid cursors return a structured 400 without resetting to the beginning.
- [ ] Re-project historical generated messages at read time using current `product_locale`.
- [ ] Run cursor tests and commit/push.

### Task 7: Enforce Complete English and Japanese Projection

- [ ] Write `mobile-localization-en`, `mobile-localization-ja`, `mobile-localization-user-content`, and `mobile-chat-locale-switch` tests.
- [ ] English generated output must contain no Hiragana, Katakana, or CJK. Japanese generated sentences must contain no untranslated English prose, with allowlisted route codes/registered names.
- [ ] Preserve `userContent` unchanged and exclude it from script validation.
- [ ] Require provider-derived navigation names to contain `en` and `ja`; use official English first, deterministic transliteration second with `localization_source=transliteration`.
- [ ] Return `route_unavailable/localization_unavailable` when a navigation name cannot be safely projected.
- [ ] Run both locale suites and commit/push.

### Task 8: Questions, Calls, and Devices

- [ ] Write `mobile-question-reply.test.js` for only-open-question composer, duplicate reply, stale question, and cross-tenant rejection.
- [ ] Consume a question atomically using scope UID before applying one answer and appending its result.
- [ ] Write `mobile-test-call-contract.test.js` for null phone, disabled calls, missing confirmation, invalid E.164, cooldown, per-user/global daily caps, and duplicate request.
- [ ] Use a durable call-attempt claim before the existing `placeCall`; do not reuse the current in-memory Map as authority.
- [ ] Add authenticated idempotent APNs PUT/DELETE storage with 64-hex token validation, environment, locale, timezone, and last-seen timestamp.
- [ ] Never permit an unauthenticated device fallback.
- [ ] Run question/call/device tests and commit/push.

### Task 9: Delete the Authenticated Account

- [ ] Write `mobile-account-deletion.test.js` for required confirmation, session revocation, provider disconnect, tenant-only cascade, idempotent replay, partial external failure, and durable receipt.
- [ ] Implement one server-side deletion orchestration using scope UID, revoking all mobile sessions and Calendar/provider connections before account data deletion.
- [ ] Return a stable receipt containing operation ID, completion time, and explicit provider cleanup status.
- [ ] Never claim completion while a required external disconnect is unknown or failed.
- [ ] Run deletion tests and commit/push.

### Task 10: Mount and Lock the Mobile Surface

- [ ] Write `mobile-v1-surface-contract.test.js` that enumerates the approved method/path matrix and rejects any location, late, recipient, approval, or attendee-send surface/import.
- [ ] Implement `handleMobileV1Request(req,res,deps)` with content type, request size limit, error envelope, bearer scope, idempotency enforcement, and no-store headers.
- [ ] Add one import and one `path.startsWith("/api/mobile/v1")` branch to `server.js` before generic routes.
- [ ] Run every `mobile-*` and provider test, then the full installed backend suite against baseline.
- [ ] Deploy staging, call each endpoint with User A/User B sessions, and verify cross-tenant rejection plus original idempotent responses.
- [ ] Commit/push, integrate, verify Railway staging commit/build identity, and record the Gate 3 receipt.

## Verification Commands

```bash
cd apps/mr-bot
node --test test/mobile-calendar-session-contract.test.js test/mobile-tenant-isolation.test.js test/mobile-profile-contract.test.js test/mobile-phone-null-contract.test.js test/mobile-analysis-terminal-state.test.js
node --test test/mobile-route-anchor.test.js test/mobile-route-projection.test.js test/mobile-route-honesty.test.js test/mobile-geocode-cost-guard.test.js test/mobile-route-provider-budget.test.js
node --test test/mobile-localization-en.test.js test/mobile-localization-ja.test.js test/mobile-localization-user-content.test.js test/mobile-chat-locale-switch.test.js test/mobile-chat-cursor.test.js
node --test test/mobile-question-reply.test.js test/mobile-test-call-contract.test.js test/mobile-account-deletion.test.js test/mobile-v1-surface-contract.test.js
npm test
git diff --check
```

Every mobile contract command must finish with zero failures. The full suite must match the clean installed baseline except for explicitly corrected assertions owned by this gate.
