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

## Task 2: Durable Provider Cursor and Same-Pass Handoff

**Files:**
- Create: `apps/life-manager/lib/event-provider-cursor.js`
- Create: `apps/life-manager/lib/event-provider-cursor.test.js`
- Modify: `apps/life-manager/lib/connector-native-runtime.js`
- Modify: `skills/connector/native-pass.js`

**Completion:** Luma candidate exhaustion advances to Connpass within the same pass; known no-effect advances candidate; provider exhaustion advances provider; unknown effect reconciles before retry; only all-provider exhaustion advances the date. Cursor survives process exit without storing page text or identity.

## Task 3: Connpass Discovery in Native Runtime

**Completion:** The official API client exhausts every page for the target date, normalizes candidates into the common inventory, runs Calendar/travel gates, and hands them to the Connpass adapter. Discovery alone never creates coverage.

## Task 4: Connpass Authenticated Registration Adapter

**Completion:** One parent-owned Connector target performs real registration, parent marker readback, PNG, admission ticket/QR or equivalent receipt, Calendar insertion, and Telegram card/photo. Only then promote Connpass registration capabilities to active.

## Task 5: Remaining Providers One at a Time

Repeat official-doc verification → read-only discovery → adapter TDD → isolated live submit → parent readback/evidence → registry promotion for Peatix, Meetup, Doorkeeper, then Eventbrite. A blocked provider advances immediately and never stops the pass.

## Task 6: Cross-Provider Live Acceptance

Existing Connector launchd starts from the first open Calendar gap and continues candidate/provider/date cursors until one real application returns provider marker, ticket/QR or equivalent admission receipt, PNG SHA, Calendar readback, and Telegram card/photo IDs in one lineage.
