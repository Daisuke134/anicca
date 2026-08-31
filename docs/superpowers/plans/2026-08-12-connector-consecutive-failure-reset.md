# Connector consecutive failure reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and subagent-driven-development. Luna writes production/tests; Sol reviews and verifies.

**Goal:** `maxConsecutiveFailures=3`を本当に連続したprovider/candidate failureだけへ適用し、成功を挟んだ離れた失敗の累積で後続providerを誤って遮断しない。

**Measured live failure:** Official wake `wake-52bdd8157305ec034d927a85`はLuma discovery success、Connpass discovery failure、Peatix discovery successと複数existing registration/bundle reuse、後続failureを経たが、counterを一度もresetしないためtotal 3で`circuit_open / provider_discovery_failed`となりEventbrite audit 0のまま停止した。Telegram positive ID `12089`、duplicate external effect 0、cleanup正常。

**Architecture:** Existing runnerのlocal `consecutiveFailures`だけを修正する。verified registered bundle reuse時だけ0へ戻す。provider discovery成功はcandidate outcome成功ではないためresetせず、候補内部のnavigate/readback/cache/direct個別successもresetしない。cross-providerを含む3 candidate/discovery outcome failureの既存circuit contractを維持する。新state/schema/retry/second wakeは作らない。

**Estimated change:** 2 files。production 1〜2 LOC、test 25〜55 LOC。

## Constraints

- Modify only `apps/mr-bot/lib/connector-minimal-runner.js` and matching test.
- RED must prove failed candidate→verified reused bundle→failed candidate is not treated as consecutive 2。
- Existing three provider/candidate failures in a row, including cross-provider failures separated only by successful discovery, still circuit before a fourth candidate outcome。
- Do not reset on navigation/readback/action-level success when the candidate outcome is still failure。
- Budgets、provider order、effect_unknown immediate stop、deadline、evidence、report schema、external stateは不変。
- Implementation/review中official wake 0、4 labels UNLOADED。

## Task 1: Restore consecutive semantics

1. Add the reused-bundle non-consecutive regression fixture and run RED against current cumulative behavior.
2. Reset only after a verified registered bundle returns `completion_disposition=reused`.
3. Run runner focused, minimal production, Harness, operations/evidence adjacent, syntax, `git diff --check`.
4. Exact two-file ownership、commit without amend。fresh Sol review SHIP後にpush。

## Completion gate

- Non-consecutive historical failure total cannot open the circuit。
- Three actual consecutive failures still stop exactly once with positive report path intact。
- Focused/adjacent PASS、fresh Sol review Critical/Important 0。

## Deferred

Push後、schedule-unloaded official foreground wakeをexact 1回再実行し、Eventbrite auditまたは`applied_bundle`まで到達する。
