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
- Modify: `skills/connector/native-pass.js`
- Modify: `skills/connector/test/native-entrypoint.test.js`

**Completion:** Native-pass reads and atomically writes mode-0600 `provider-cursor.json` through the Task 2A store, forwards it into the next wake, and removes the superseded Luma-only `cursor.json` path after migration tests pass.

## Task 3: Connpass Discovery in Native Runtime

**Completion:** The official API client exhausts every page for the target date, normalizes candidates into the common inventory, runs Calendar/travel gates, and hands them to the Connpass adapter. Discovery alone never creates coverage.

## Task 4: Connpass Authenticated Registration Adapter

**Completion:** One parent-owned Connector target performs real registration, parent marker readback, PNG, admission ticket/QR or equivalent receipt, Calendar insertion, and Telegram card/photo. Only then promote Connpass registration capabilities to active.

## Task 5: Remaining Providers One at a Time

Repeat official-doc verification → read-only discovery → adapter TDD → isolated live submit → parent readback/evidence → registry promotion for Peatix, Meetup, Doorkeeper, then Eventbrite. A blocked provider advances immediately and never stops the pass.

## Task 6: Cross-Provider Live Acceptance

Existing Connector launchd starts from the first open Calendar gap and continues candidate/provider/date cursors until one real application returns provider marker, ticket/QR or equivalent admission receipt, PNG SHA, Calendar readback, and Telegram card/photo IDs in one lineage.
