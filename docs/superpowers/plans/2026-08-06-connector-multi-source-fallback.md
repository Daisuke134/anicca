# Connector Calendar-First Multi-Source Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Every behavior change uses test-driven-development and verification-before-completion.

**Goal:** Keep applying to Calendar-compatible events across providers until one verified registration with usable admission evidence is delivered.

**Architecture:** Life Manager owns one ordered provider registry and one durable provider cursor. Provider adapters implement the same discovery, registration, effect-readback, screenshot, and ticket/QR contract. Ranking changes order only; Calendar/travel, provider availability, and existing spend caps remain safety gates. A candidate or provider failure advances the cursor rather than ending the pass.

**Provider order:** Luma → Connpass → Peatix → Meetup → Doorkeeper → Eventbrite.

## Task 1: Closed Provider Capability Registry

**Files:**
- Create: `apps/life-manager/lib/event-provider-registry.js`
- Create: `apps/life-manager/lib/event-provider-registry.test.js`
- Modify: `apps/life-manager/package.json`

**Contract:**
- Every provider declares exactly `discovery`, `registration`, `effect_readback`, `screenshot_evidence`, and `ticket_or_qr`.
- Each capability is one of `active`, `advisory_only`, or `blocked` with a bounded safe reason.
- Luma starts active from existing live proof. Connpass starts discovery active and all write/evidence abilities advisory-only until live promotion. Remaining providers start blocked until their official discovery/auth constraints are measured.
- Registry is ordered, immutable, content-addressed, contains no credential values, and rejects unknown providers/capabilities/statuses.

- [x] Write failing tests for exact provider order, exact capability keys, no secret values, immutable provenance, and fail-closed promotion.
- [x] Run `node --test lib/event-provider-registry.test.js` and observe module-not-found RED.
- [x] Implement the minimal registry and promotion validator.
- [x] Add the test to `test:outbound`; focused 3/3、pretest 12/12、outbound 340/340 GREEN。
- [x] Update master spec with RED/GREEN evidence; commit and push.

## Task 2A: Durable Provider Cursor Contract

**Files:**
- Create: `apps/life-manager/lib/event-provider-cursor.js`
- Create: `apps/life-manager/lib/event-provider-cursor.test.js`

**Completion:** A mode-0600 atomic cursor stores only date, provider, candidate index, generation, and observed time. Exact transitions advance candidate, then provider, then date; unknown effect cannot advance. Forged/stale cursors and provider-order drift fail closed.

- [x] Module-not-found REDを確認。
- [x] Forward-only cursor、0600 atomic store、forgery/order-drift rejectionを実装。
- [x] Focused 6/6、pretest 12/12、outbound 343/343 GREEN。
- [x] Master specへ進捗130を記録しcommit/push。

## Task 2B1: Same-Pass Runtime State Transition

**Files:**
- Modify: `apps/life-manager/lib/connector-native-runtime.js`
- Modify: `apps/life-manager/lib/connector-native-runtime.test.js`

**Completion:** The runtime accepts only a verified Task 2A provider cursor. Known no-effect advances the candidate, Luma exhaustion advances to Connpass, and unknown effect cannot advance before readback reconciliation. It emits the next bounded provider cursor without storing page text or identity. Actual Connpass discovery remains Task 3.

The slice is 127 changed lines across its two declared files because the existing runtime fixture requires a complete Calendar/profile/spend/write boundary setup; production logic is 60 lines and splitting the single transition contract again would create an unverified half-state.

- [x] RED: existing 15 tests passed and the missing `provider_cursor` assertion failed.
- [x] GREEN: verified cursor advances known-no-effect candidate then Luma exhaustion to Connpass; unknown-effect readback leaves cursor unchanged.
- [x] Focused 16/16、pretest 12/12、outbound 344/344 GREEN。
- [x] Master specへ進捗131を記録しcommit/push。

## Task 2B2: Native-Pass Provider Cursor Persistence

**Files:**
- Modify: `apps/life-manager/lib/connector-native-runtime.js`
- Modify: `skills/connector/native-pass.js`
- Modify: `skills/connector/test/native-entrypoint.test.js`

**Completion:** Native-pass reads and atomically writes mode-0600 `provider-cursor.json` through the Task 2A store, forwards it into the next wake, and removes the superseded Luma-only `cursor.json` path after migration tests pass.

The runtime file needs an 11-line first-wake initializer because native-pass cannot know the first open date. The total 112 changed lines across three files mostly delete the old cursor validator/writer; splitting migration from persistence would temporarily leave two active cursor SSOTs.

- [x] RED: native-entrypoint existing 25 tests passed and `provider-cursor.json` was absent.
- [x] GREEN: Task 2A store owns read/write, first wake initializes from the first open date, next wake receives the same cursor, and legacy `cursor.json` is removed only after successful new-state recording.
- [x] Native-entrypoint 26/26、runtime 16/16、pretest 12/12、outbound 344/344 GREEN。
- [x] Master specへ進捗132を記録しcommit/push。

## Task 3A: Connpass Official-API Runtime Handoff

**Files:**
- Modify: `apps/life-manager/lib/connector-native-runtime.js`
- Modify: `apps/life-manager/lib/connector-native-runtime.test.js`
- Modify: `skills/connector/native-pass.js`

**Completion:** A Connpass provider cursor invokes the existing exhaustive official-v2 API handoff for its date in the same runtime pass. The API key remains private, missing/unavailable API stays open, normalized discovery is advisory-only, and discovery never creates coverage or invokes registration.

- [x] RED: existing runtime 16 tests passed and the Connpass cursor never invoked handoff.
- [x] GREEN: both a resumed Connpass cursor and same-pass Luma exhaustion invoke official-v2 handoff; missing key is zero-network/open and discovered candidates remain advisory with coverage credit zero.
- [x] Runtime 17/17、native-entrypoint 26/26、pretest 12/12、outbound 345/345 GREEN。
- [x] Master specへ進捗133を記録しcommit/push。

## Task 3B: Provider-Neutral Calendar and Travel Gate

**Files:**
- Modify: `apps/life-manager/lib/calendar-candidate-gate.js`
- Modify: `apps/life-manager/lib/calendar-candidate-gate.test.js`
- Modify: `apps/life-manager/lib/connector-native-runtime.js`
- Modify: `apps/life-manager/lib/connector-native-runtime.test.js`

**Completion:** Verified Connpass discovery candidates pass through the same direct-conflict, all-day, inbound-route, outbound-route, and expanded-window checks as Luma without forging Luma provenance. Only eligible candidates are handed to the still-read-only Connpass adapter boundary; zero eligible candidates advances the provider cursor and coverage remains open.

This slice changes 196 lines across four files because 60 lines move the existing Luma evaluator into one shared implementation, while separate unit and runtime tests prove both provenance rejection and cursor advancement. Splitting before runtime wiring would leave the new gate unreachable and would not satisfy Task 3.

- [x] RED: existing Calendar gate 5 tests passed and the Connpass evaluator export was absent.
- [x] GREEN: Luma and Connpass share one evaluator; verified Connpass candidates receive direct/all-day/travel/expanded-window checks; fake handoff fails closed; zero eligible advances to Peatix.
- [x] Focused Calendar 6/6 + runtime 17/17、pretest 12/12、outbound 346/346 GREEN。
- [x] Master specへ進捗134を記録しcommit/push。

## Task 4: Connpass Authenticated Registration Adapter

**Completion:** One parent-owned Connector target performs real registration, parent marker readback, PNG, admission ticket/QR or equivalent receipt, Calendar insertion, and Telegram card/photo. Only then promote Connpass registration capabilities to active.

## Task 5: Remaining Providers One at a Time

Repeat official-doc verification → read-only discovery → adapter TDD → isolated live submit → parent readback/evidence → registry promotion for Peatix, Meetup, Doorkeeper, then Eventbrite. A blocked provider advances immediately and never stops the pass.

## Task 6: Cross-Provider Live Acceptance

Existing Connector launchd starts from the first open Calendar gap and continues candidate/provider/date cursors until one real application returns provider marker, ticket/QR or equivalent admission receipt, PNG SHA, Calendar readback, and Telegram card/photo IDs in one lineage.
