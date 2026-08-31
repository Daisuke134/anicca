# Connector Eventbrite fallback dispatch 19E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and subagent-driven-development. Luna writes production/tests; Sol reviews and verifies.

**Goal:** Review済みEventbrite workflowをproduction Browser Harness `runFallback`のexact provider dispatchへ接続し、安全なEventbrite action sequenceとofficial readbackをbounded adapterから到達可能にする。

**Architecture:** 既存Harness、Eventbrite inspector/action/readback、Browser Harness adapterを再利用する。`runFallback`のworkflow mapへ`eventbrite`を一項目加えるだけで、action semantics、retry loop、agent、state、browser railは増やさない。既存`effect_unknown` propagationにより、ticket/final mutation後の未確認効果はadapterを即停止し同じfallback内で再操作しない。

**Estimated change:** 2 files。production 1 LOC、test 70〜130 LOC。

## Constraints

- Modify only `apps/mr-bot/lib/connector-production-browser-harness.js` and matching test.
- Eventbrite exact candidate/current URL、same-event child frame、既存control/readback contractを変更しない。
- RED must prove current `runFallback({provider:"eventbrite"})` rejects before Eventbrite workflow dispatch.
- GREEN success must use Eventbrite workflow readback, never Luma readback, and return `completed` with bounded repaired actions.
- A final or ticket action returning `effect_unknown` must operate exact1, return `failed/effect_unknown`, and make no second proposal/operation/readback mutation.
- No factory/native/runner/operations/evidence/Calendar/Telegram/schedule change; official wake 0; four Connector labels UNLOADED.

## Task 1: Add exact Eventbrite workflow dispatch

1. Add focused `runFallback` tests for safe Eventbrite success and effect-unknown no-retry. Run RED and capture the existing missing-map failure.
2. Add `eventbrite: eventbriteWorkflow` to the existing exact workflow map.
3. Run Harness focused, Eventbrite workflow, Browser Harness adapter, minimal production adjacent, syntax, and `git diff --check`.
4. Confirm exact two-file ownership, commit without amend. Push only after fresh Sol review SHIP.

## Completion gate

- `runFallback` exact Eventbrite dispatch succeeds only through existing safe action/readback contracts.
- Effect-unknown mutation count exact1 and retry count0.
- Focused/adjacent PASS; fresh Sol review Critical/Important 0.

## Deferred

Native provider order、official production wake、Calendar/evidence/Telegram `applied_bundle`、schedule load。
