# Connector Doorkeeper visible eligibility control 19D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and subagent-driven-development. Luna writes production/tests; Sol reviews and live-verifies.

**Goal:** Doorkeeper detail eligibilityが、closed modalのvisible registration trigger 1件を正しく受付中と判定し、hidden final submitを重複triggerとして数えないようにする。

**Measured cause:** Official pages [`techgym/198719`](https://techgym.doorkeeper.jp/events/198719), [`mitakarb/198198`](https://mitakarb.doorkeeper.jp/events/198198), and [`weeyble/198733`](https://weeyble.doorkeeper.jp/events/198733) all contain one visible `a[href="#new_registration_modal"]` labelled `申し込む` plus one hidden modal `input[type="submit"][value="申し込む"]`. The detail reader preserves visibility, but `normalizeDetail` counts both controls and requires total count 1, so valid events are rejected. JSON-LD on the first two reports Offline, InStock, price 0 JPY and exact event URL.

**Architecture:** Change only the eligibility count to exact **visible** `申し込む` controls. Hidden final submit remains available to the later modal inspector after activation; no click or submit behavior changes.

**Estimated change:** 2 files。production 1 LOC、test 2〜10 LOC。

## Constraints and task

- Modify only `apps/mr-bot/lib/connector-doorkeeper-workflow.js` and matching test.
- RED fixture has one visible trigger and one hidden final submit with the same label; eligible candidate must currently be rejected.
- GREEN filters exact submit-label controls by `visible === true` before requiring exactly one.
- Duplicate visible triggers still fail closed; hidden control alone still fails; unavailable/payment/JSON-LD/calendar contracts remain unchanged.
- Run focused Doorkeeper, minimal production + Harness adjacent, syntax, and diff checks. Exact two-file commit/push; no official wake during implementation.

## Live completion gate

After fresh Sol SHIP and stable integration, run exactly one official foreground wake with schedule unloaded. Doorkeeper `eligible_count` must become positive or the next exact boundary must be evidenced. External registration is complete only with the existing parent readback and applied-bundle chain.

## Result

Luna added one current-DOM fixture value and changed one production predicate. RED was `14/15`; filtering exact-label controls by visibility before the exactly-one check produced GREEN `15/15`, with Harness + Doorkeeper adjacent `87/87`.

Fresh Sol review returned SHIP with Critical/Important 0. Sol independently repeated `15/15`, `87/87`, syntax, diff, ownership, remote equality, and four-label unloaded checks. Reviewed commit `fdbd624c7` was fast-forwarded into stable. No live wake or external effect occurred during implementation.
