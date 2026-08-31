# Connector Eventbrite factory injection 19E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and subagent-driven-development. Luna writes production/tests; Sol reviews and verifies.

**Goal:** Official production factoryが生成したEventbrite workflowをdefault Browser Harnessへ渡し、後続のEventbrite fallback dispatchが同じreview済みworkflowでprovider readbackできる状態にする。

**Architecture:** 既存`createEventbriteScriptFirstWorkflow`、provider router、Browser Harnessをそのまま再利用する。factoryのHarness constructionへ既存workflow参照を一つ渡すだけで、新しいprovider abstraction、agent、browser rail、stateは作らない。

**Estimated change:** 2 files。production 1 LOC、test 20〜40 LOC。

## Constraints

- Modify only `apps/mr-bot/lib/connector-minimal-production.js` and matching test.
- RED must prove the default factory-created Harness—not an injected Harness—receives the factory Eventbrite workflow and uses its `readProviderState` after a safe mocked final action.
- Browser session/target、実Eventbrite、Calendar、evidence、Telegram、schedule作用は0。
- Luma/Connpass/Peatix/Meetup/Doorkeeper wiringとprovider orderは不変。
- Eventbrite `runFallback` provider mapとnative provider orderは後続sliceまで変更しない。
- all four Connector labels remain UNLOADED.

## Task 1: Pass the existing Eventbrite workflow into the default Harness

1. Default Browser Harnessをfactoryから構築するfocused testを追加し、Eventbrite workflowの`readProviderState`が未注入のため到達しないREDを確認する。
2. `eventbriteWorkflow`を`createProductionBrowserHarness`へ既存provider参照と並べて渡す。
3. Factory focused、Browser Harness、Eventbrite workflow、syntax、`git diff --check`を実行する。
4. Exact two-file ownershipを確認し、commit without amend。fresh Sol reviewがSHIP後にpushする。

## Completion gate

- Factory-created default Harnessが同じEventbrite workflowを保持する。
- External effect 0、official wake 0。
- Focused/adjacent PASS、fresh Sol review Critical/Important 0。

## Deferred

Eventbrite `runFallback` dispatch map・effect-unknown retry guardのintegration、native provider order、実production wake、Calendar/evidence/Telegram `applied_bundle`。
