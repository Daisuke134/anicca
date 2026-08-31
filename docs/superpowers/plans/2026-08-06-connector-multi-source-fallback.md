# Connector Calendar-First Multi-Source Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Every behavior change uses test-driven-development and verification-before-completion.

**Goal:** Keep applying to Calendar-compatible events across providers until one verified registration with usable admission evidence is delivered.

**Architecture:** Mr.bot owns one ordered provider registry and one durable provider cursor. Provider adapters implement the same discovery, registration, effect-readback, screenshot, and ticket/QR contract. Ranking changes order only; Calendar/travel, provider availability, and existing spend caps remain safety gates. A candidate or provider failure advances the cursor rather than ending the pass.

**Provider order:** Luma → Connpass → Peatix → Meetup → Doorkeeper → Eventbrite.

## Task 1: Closed Provider Capability Registry

**Files:**
- Create: `apps/mr-bot/lib/event-provider-registry.js`
- Create: `apps/mr-bot/lib/event-provider-registry.test.js`
- Modify: `apps/mr-bot/package.json`

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
- Create: `apps/mr-bot/lib/event-provider-cursor.js`
- Create: `apps/mr-bot/lib/event-provider-cursor.test.js`

**Completion:** A mode-0600 atomic cursor stores only date, provider, candidate index, generation, and observed time. Exact transitions advance candidate, then provider, then date; unknown effect cannot advance. Forged/stale cursors and provider-order drift fail closed.

- [x] Module-not-found REDを確認。
- [x] Forward-only cursor、0600 atomic store、forgery/order-drift rejectionを実装。
- [x] Focused 6/6、pretest 12/12、outbound 343/343 GREEN。
- [x] Master specへ進捗130を記録しcommit/push。

## Task 2B1: Same-Pass Runtime State Transition

**Files:**
- Modify: `apps/mr-bot/lib/connector-native-runtime.js`
- Modify: `apps/mr-bot/lib/connector-native-runtime.test.js`

**Completion:** The runtime accepts only a verified Task 2A provider cursor. Known no-effect advances the candidate, Luma exhaustion advances to Connpass, and unknown effect cannot advance before readback reconciliation. It emits the next bounded provider cursor without storing page text or identity. Actual Connpass discovery remains Task 3.

The slice is 127 changed lines across its two declared files because the existing runtime fixture requires a complete Calendar/profile/spend/write boundary setup; production logic is 60 lines and splitting the single transition contract again would create an unverified half-state.

- [x] RED: existing 15 tests passed and the missing `provider_cursor` assertion failed.
- [x] GREEN: verified cursor advances known-no-effect candidate then Luma exhaustion to Connpass; unknown-effect readback leaves cursor unchanged.
- [x] Focused 16/16、pretest 12/12、outbound 344/344 GREEN。
- [x] Master specへ進捗131を記録しcommit/push。

## Task 2B2: Native-Pass Provider Cursor Persistence

**Files:**
- Modify: `apps/mr-bot/lib/connector-native-runtime.js`
- Modify: `skills/connector/native-pass.js`
- Modify: `skills/connector/test/native-entrypoint.test.js`

**Completion:** Native-pass reads and atomically writes mode-0600 `provider-cursor.json` through the Task 2A store, forwards it into the next wake, and removes the superseded Luma-only `cursor.json` path after migration tests pass.

The runtime file needs an 11-line first-wake initializer because native-pass cannot know the first open date. The total 112 changed lines across three files mostly delete the old cursor validator/writer; splitting migration from persistence would temporarily leave two active cursor SSOTs.

- [x] RED: native-entrypoint existing 25 tests passed and `provider-cursor.json` was absent.
- [x] GREEN: Task 2A store owns read/write, first wake initializes from the first open date, next wake receives the same cursor, and legacy `cursor.json` is removed only after successful new-state recording.
- [x] Native-entrypoint 26/26、runtime 16/16、pretest 12/12、outbound 344/344 GREEN。
- [x] Master specへ進捗132を記録しcommit/push。

## Retired transport record: Connpass API (not a task)

Progress 145 permanently supersedes this transport. It is retained only as commit history; it is not an executable task or architecture option. The active Connector runtime MUST NOT read a Connpass API key, call the Connpass API, or derive availability from an API response. Task 4B2D is the sole replacement.

## Task 3B: Provider-Neutral Calendar and Travel Gate

**Files:**
- Modify: `apps/mr-bot/lib/calendar-candidate-gate.js`
- Modify: `apps/mr-bot/lib/calendar-candidate-gate.test.js`
- Modify: `apps/mr-bot/lib/connector-native-runtime.js`
- Modify: `apps/mr-bot/lib/connector-native-runtime.test.js`

**Completion:** Verified Connpass discovery candidates pass through the same direct-conflict, all-day, inbound-route, outbound-route, and expanded-window checks as Luma without forging Luma provenance. Only eligible candidates are handed to the still-read-only Connpass adapter boundary; zero eligible candidates advances the provider cursor and coverage remains open.

This slice changes 196 lines across four files because 60 lines move the existing Luma evaluator into one shared implementation, while separate unit and runtime tests prove both provenance rejection and cursor advancement. Splitting before runtime wiring would leave the new gate unreachable and would not satisfy Task 3.

- [x] RED: existing Calendar gate 5 tests passed and the Connpass evaluator export was absent.
- [x] GREEN: Luma and Connpass share one evaluator; verified Connpass candidates receive direct/all-day/travel/expanded-window checks; fake handoff fails closed; zero eligible advances to Peatix.
- [x] Focused Calendar 6/6 + runtime 17/17、pretest 12/12、outbound 346/346 GREEN。
- [x] Master specへ進捗134を記録しcommit/push。

## Authorized Browser-Write Premise

Dais confirms he has obtained direct permission from each listed event site for Connector browser registration. Treat that direct authorization as the operative write permission; do not revive the rejected inference that public generic documents prohibit these approved account actions. Provider writes still require the fixed allowlist, Connector-owned `:9222` target, existing spend/Calendar gates, parent effect readback, and external evidence.

## Task 4A: Provider-Neutral Parent-Owned Browser Rail

**Files:**
- Modify: `apps/mr-bot/lib/cloakbrowser-daily-driver.js`
- Modify: `apps/mr-bot/lib/cloakbrowser-daily-driver.test.js`
- Modify: `apps/mr-bot/lib/connector-tab-owner.js`
- Modify: `apps/mr-bot/lib/connector-tab-owner.test.js`

**Completion:** The existing `createTarget → claimExact → probe → heartbeat → goto → parent task/readback → release` lifecycle accepts only the fixed provider/host mapping for Luma, Connpass, Peatix, Meetup, Doorkeeper, and Eventbrite. `withLumaPage` remains a compatibility wrapper. Endpoint stays exactly Connector `:9222`; Gig `:9223` and arbitrary origins remain rejected.

This slice changes 103 lines across the four declared files because both the live-target and fallback-tab ownership paths share the same URL boundary; splitting them would leave one path Luma-only and create inconsistent fencing.

- [x] RED: existing ownership 12 tests passed; `withEventPage` was absent and tab owner rejected Connpass.
- [x] GREEN: fixed provider-host mapping shares the exact parent-owned lifecycle; Luma compatibility remains; mismatch/arbitrary origin/credentials/`:9223` fail closed.
- [x] Ownership focused 22/22、pretest 12/12、outbound 348/348 GREEN。
- [x] Master specへdirect authorization premiseと進捗135を記録しcommit/push。

## Task 4B1: Connpass Parent Readback and Submit Adapter

**Files:**
- Create: `apps/mr-bot/lib/connpass-browser-provider.js`
- Create: `apps/mr-bot/lib/connpass-browser-provider.test.js`
- Modify: `apps/mr-bot/package.json`

**Completion:** The adapter uses only `dailyDriver.withEventPage("connpass", ...)`, recognizes absent/login-required/registered/pending markers by parent readback, performs only exact approved registration controls, distinguishes known-no-effect from unknown effect, and captures a full-page PNG only after parent readback proves registration or pending approval.

The closed adapter and its contract tests total 258 lines. Splitting readback from submit would create a callable submit path without reconciliation, while splitting screenshot proof would allow an unproven success result; those half-states violate the required transaction boundary.

- [x] Module-not-found REDを確認。
- [x] Parent readback、exact control、known/unknown effect、registered/pending後だけPNG proofを実装。
- [x] Focused 3/3、pretest 12/12、constant outbound suite 348/348 GREEN。
- [x] Master specへ進捗136を記録しcommit/push。

## Task 4B2A: Common Verified Provider Event Inventory

**Completion:** Calendar-eligible Connpass candidates become an immutable, content-addressed, provenance-checked provider event inventory that preserves event ref, canonical URL, time, venue, and source handoff lineage without pretending to be Luma. Calendar sync and the write pipeline accept Luma or this verified common inventory only.

The slice spans seven files because one new SSOT contract must be produced by runtime and consumed at both independent write gates (pipeline and Calendar); tests and constant-suite registration cover those three boundaries. Production changes outside the new module total 23 lines.

- [x] Module-not-found REDを確認。
- [x] Immutable/content-addressed Connpass inventory、handoff/coverage provenance、runtime productionを実装。
- [x] Calendar syncとwrite pipelineをLuma-or-verified-provider inventoryへ拡張。
- [x] Focused 46/46、pretest 12/12、constant outbound suite 348/348 GREEN。
- [x] Master specへ進捗137を記録しcommit/push。

## Task 4B2B: Connpass Job and Evidence Receipt

**Completion:** A Connpass-specific deterministic runtime job, effect key, adapter execution/reconciliation, and provider evidence store produce the same E1/E2/E3 verified outbound receipt contract without Luma refs or paths.

The job/adapter/evidence transaction totals 348 lines across four modules/tests plus constant-suite registration. Splitting the evidence store from execution would leave the adapter unable to produce a verifier receipt; splitting reconciliation would permit duplicate effects after uncertainty.

- [x] Both modules missing REDを確認。
- [x] Deterministic Connpass job/effect key、inspect→submit fence、unknown reconciliation、E1/E2/E3 receiptを実装。
- [x] Mode-0600 immutable Connpass PNG/receipt/object storeを実装。
- [x] Focused 4/4、pretest 12/12、constant outbound suite 348/348 GREEN。
- [x] Master specへ進捗138を記録しcommit/push。

## Task 4B2C1: Provider-Neutral Downstream Write Contracts

**Completion:** The common write pipeline, registration coverage evidence, bounded result, candidate-attempt, and Telegram lineage accept a verified Connpass provider inventory and Connpass event reference without requiring a fabricated Luma goal decision. Existing Luma verification remains unchanged.

This slice owns only downstream contract acceptance and regression tests. It does not construct a Connpass provider or perform a browser effect.

- [x] Complete in commit `65241d6a2`; progress 141.

## Task 4B2C2: Connpass Runtime Execution Wiring

**Completion:** Calendar-eligible Connpass candidates enter the common write pipeline with the Connpass provider/job/evidence dependencies, then Calendar and Telegram lineage. Known no-effect advances candidate/provider without stopping the pass; unknown effect reconciles before retry.

- [x] Complete in commits `e822bfa3a`, `d0e05f5d8`, and `1cfa2e56f`; progress 143–145.

## Task 4B2D: Connpass Browser-Only Discovery

**Completion:** The active runtime uses only Connector CloakBrowser `:9222` parent-owned targets to read official Connpass calendar/explore pages, creates a verified exhaustive event inventory for the cursor date, and calls no Connpass API. API key presence or absence cannot change this path.

- [ ] Read public event cards from a fixed official Connpass discovery URL through the parent-owned daily driver.
- [ ] Normalize exact date, event URL/ref, title, start, and venue without raw page text or identity state.
- [ ] Feed the verified browser inventory through Calendar/travel gate and the existing Connpass write dependencies.
- [ ] Prove API-key reference 0 and API network call 0 in focused/full tests and a live launchd run.

## Task 4B3: Connpass Live Submit and Promotion

**Completion:** The existing Connector launchd/browser account performs one real approved-site registration. Parent marker readback, PNG SHA, admission ticket/QR or equivalent receipt, Calendar readback, Telegram card/photo IDs share one event lineage; only then promote Connpass write capabilities to active.

## Task 5: Remaining Providers One at a Time

Repeat official-doc verification → read-only discovery → adapter TDD → isolated live submit → parent readback/evidence → registry promotion for Peatix, Meetup, Doorkeeper, then Eventbrite. A blocked provider advances immediately and never stops the pass.

## Task 6: Cross-Provider Live Acceptance

Existing Connector launchd starts from the first open Calendar gap and continues candidate/provider/date cursors until one real application returns provider marker, ticket/QR or equivalent admission receipt, PNG SHA, Calendar readback, and Telegram card/photo IDs in one lineage.
