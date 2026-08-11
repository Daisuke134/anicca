# Connector Eventbrite native provider order 19E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and subagent-driven-development. Luna writes production/tests; Sol reviews and verifies.

**Goal:** Review済みEventbrite factory/router/Harness/workflowをofficial bounded native wakeから到達可能にする。

**Architecture:** Frozen provider orderの末尾へ`eventbrite`を一項目追加する。既存`runMinimalConnectorWake`、budgets、private profile、failure circuit、browser railを変更しない。

**Estimated change:** 2 files。production 1 LOC、test 3 LOC。

## Constraints

- Modify only `skills/connector/native-pass.js` and `skills/connector/test/native-entrypoint.test.js`.
- Exact order is `luma → connpass → peatix → meetup → doorkeeper → eventbrite`.
- `maxConsecutiveFailures=3`、`maxWakeMs=600000`、`maxAgentSteps=10`は不変。
- Private attendee identityはdependency factoryだけに渡しwake inputへ入れない既存contractを維持する。
- No official wake/browser/provider/Calendar/evidence/Telegram effect during implementation; four labels UNLOADED.

## Task 1: Add Eventbrite to the frozen native order

1. Existing exact-order assertions 3件へEventbrite末尾を追加し、旧5-providerとの差分だけがREDになることを確認する。
2. `DEFAULT_PROVIDERS`末尾へ`eventbrite`を一項目追加する。
3. Native entrypoint、minimal runner、minimal production、Harness、Eventbrite workflow、syntax、`git diff --check`を実行する。
4. Exact two-file ownership、commit without amend。fresh Sol review SHIP後にpushする。

## Completion gate

- Official native passのexact provider orderが6 providerになる。
- Budgets/private boundary不変。
- Focused/adjacent PASS、fresh Sol review Critical/Important 0。

## Deferred

Schedule-unloaded official production wakeによる実Eventbrite applied bundle、Calendar/evidence/Telegram、final schedule load。
