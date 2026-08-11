# Connector consecutive failure reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and subagent-driven-development. Luna writes production/tests; Sol reviews and verifies.

**Goal:** `maxConsecutiveFailures=3`を本当に連続したprovider/candidate failureだけへ適用し、成功を挟んだ離れた失敗の累積で後続providerを誤って遮断しない。

**Measured live failure:** Official wake `wake-52bdd8157305ec034d927a85`はLuma discovery success、Connpass discovery failure、Peatix discovery successと複数existing registration/bundle reuse、後続failureを経たが、counterを一度もresetしないためtotal 3で`circuit_open / provider_discovery_failed`となりEventbrite audit 0のまま停止した。Telegram positive ID `12089`、duplicate external effect 0、cleanup正常。

**Architecture:** Existing runnerのlocal `consecutiveFailures`だけを修正する。verified provider discovery成功時とverified registered bundle reuse時に0へ戻す。候補内部のnavigate/readback/cache/direct個別successではresetせず、同一provider内で3候補が連続失敗する既存circuit contractを維持する。新state/schema/retry/second wakeは作らない。

**Estimated change:** 2 files。production 2〜4 LOC、test 45〜80 LOC。

## Constraints

- Modify only `apps/life-manager/lib/connector-minimal-runner.js` and matching test.
- RED must prove failure→successful verified provider discovery→failure→failure does not circuit at total historical 3。
- RED must prove failed candidate→verified reused bundle→failed candidate is not treated as consecutive 2。
- Existing three provider discovery failures in a row and three candidate failures in a row still circuit before a fourth browser action。
- Do not reset on navigation/readback/action-level success when the candidate outcome is still failure。
- Budgets、provider order、effect_unknown immediate stop、deadline、evidence、report schema、external stateは不変。
- Implementation/review中official wake 0、4 labels UNLOADED。

## Task 1: Restore consecutive semantics

1. Add the two non-consecutive regression fixtures and run RED against current cumulative behavior.
2. Reset only after verified discovery and verified registered bundle reuse.
3. Run runner focused, minimal production, Harness, operations/evidence adjacent, syntax, `git diff --check`.
4. Exact two-file ownership、commit without amend。fresh Sol review SHIP後にpush。

## Completion gate

- Non-consecutive historical failure total cannot open the circuit。
- Three actual consecutive failures still stop exactly once with positive report path intact。
- Focused/adjacent PASS、fresh Sol review Critical/Important 0。

## Deferred

Push後、schedule-unloaded official foreground wakeをexact 1回再実行し、Eventbrite auditまたは`applied_bundle`まで到達する。
