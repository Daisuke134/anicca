# Connector O1A-02 Runtime Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** O1A-01でenqueueしたConnector event application jobを、既存workerがleaseを失わずにclaimし、既存PostgreSQL protocolでretryまたはdead-letterへ確実に遷移できるようにする。

**Architecture:** `lm_runtime_jobs`と既存SQL functionを唯一のqueue/state machineとして維持する。worker実行中だけtenant・job・attempt・workerでscopedされたheartbeatを定期送信し、イベント選定やLuma操作の判断は追加しない。Connector capability固有のPostgreSQL integration scenarioでenqueue/idempotency/claim/heartbeat/retry/dead-letterを一続きに検証する。

**Tech Stack:** Node.js 20、CommonJS、`node:test`、PostgreSQL 18、Docker integration test

## Global Constraints

- 正本は`docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`。
- 実装順はO1A→O1B→O1C→Order 2→3A→3B→4→5→Webから変更しない。
- 新しいqueue、browser、secret store、runtimeを作らない。
- コードはlease更新と状態遷移だけを扱い、イベント評価・候補選択・終了判断をhardcodeしない。
- 外部効果jobの状態が不明ならretryせず`reconciling`へ送る既存fail-closed規則を維持する。
- production codeより先に失敗testを実行し、commit前にfresh verificationを実行する。
- ユーザーの明示指示により既存`main`で連続実行し、対象ファイルだけをcommit・pushする。

---

### Task 1: Worker lease heartbeat

**Files:**
- Create: `apps/life-manager/lib/runtime-lease-heartbeat.js`
- Create: `apps/life-manager/lib/runtime-lease-heartbeat.test.js`
- Modify: `apps/life-manager/scripts/runtime-up.js`
- Modify: `apps/life-manager/scripts/runtime-up.test.js`

**Interfaces:**
- Consumes: `heartbeatJob({tenantId, jobId, attempt, workerId, leaseSeconds}, storeOptions)`
- Produces: `startRuntimeLeaseHeartbeat(input, dependencies)` returning `{ stop(): Promise<void> }`
- `executeCapabilityJob(job, services)` starts heartbeat before adapter execution and stops it before completion/failure mutation.

- [x] **Step 1: failing heartbeat testsを書く**

  `runtime-lease-heartbeat.test.js`へ、制御可能なtimerで一回pulseさせた時に正確なtenant/job/attempt/worker/leaseが既存`heartbeatJob`へ渡ること、同時pulseが直列化されること、`stop()`がtimerを解除し最後のpulseを待つことを書く。`runtime-up.test.js`へ、外部効果handler実行中のheartbeat失敗を`unknownEffect=true`として`failJob`へ渡すtestを書く。

- [x] **Step 2: REDを確認する**

  Run: `node --test lib/runtime-lease-heartbeat.test.js scripts/runtime-up.test.js`

  Expected: `Cannot find module './runtime-lease-heartbeat.js'`または未接続heartbeat assertionでFAIL。

- [x] **Step 3: 最小実装を書く**

  `startRuntimeLeaseHeartbeat`は固定machine identityだけを扱い、intervalは`leaseSeconds * 1000 / 3`、最小1000msとする。pulseはpromise chainで直列化し、最初の失敗を保存する。`stop()`はinterval解除後にin-flight pulseを待ち、保存した失敗をthrowする。`runtime-up.js`のproduction workerは既存`heartbeatJob`と同じlease秒を`executeCapabilityJob`へ渡す。

- [x] **Step 4: GREENとworker回帰testを確認する**

  Run: `node --test lib/runtime-lease-heartbeat.test.js scripts/runtime-up.test.js`

  Expected: 全test PASS、warning/errorなし。

---

### Task 2: Connector PostgreSQL lifecycle proof

**Files:**
- Modify: `apps/life-manager/test/postgres/runtime-job-protocol.integration.sh`
- Modify: `apps/life-manager/package.json`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

**Interfaces:**
- Consumes: `outbound.event.apply` job contract and existing SQL functions `claim_lm_runtime_jobs`、`heartbeat_lm_runtime_job`、`fail_lm_runtime_job`
- Produces: one reproducible integration proof that a duplicate enqueue stays one row and bounded known-before-submit failures end in `dead_letter`.

- [x] **Step 1: Connector lifecycle characterizationを追加する**

  integration scriptに`outbound.event.apply`、`effect_class=publish`、安定effect key、`max_attempts=2`のjobを二回enqueueし、一行だけになることを要求する。claim後heartbeatが同じattemptを維持し、`unknown_effect=false`の失敗一回目が`queued`、二回目が`dead_letter`、failed receiptが二行になることを要求する。

- [x] **Step 2: 既存SQL protocolでlifecycleを実測する**

  Run: `npm run test:runtime-job:postgres`

  Expected: Connector固有scenarioを含めてPASS。ここは既存SQL state machineのcharacterizationであり、
  production変更のTDD REDはTask 1で実施する。

- [x] **Step 3: lifecycle wiringを完成する**

  新しいtable/functionを作らず、既存SQL APIだけでConnector scenarioを通す。packageの`test:outbound`へheartbeat unit testを追加し、正本specへ実行証拠を記録する。

- [x] **Step 4: fresh verificationを実行する**

  Run: `npm run test:outbound && npm run test:runtime-up && npm run test:runtime-job:postgres && git diff --check`

  Expected: 全command exit 0。

- [x] **Step 5: spec更新、commit、push、remote一致確認**

  O1A-02を完了へ変更し、test件数と実装commitを記録する。対象ファイルとplan/specだけをcommitして`origin/main`へpushし、`git rev-parse HEAD`と`git ls-remote origin refs/heads/main`を一致させる。

  Evidence: `test:outbound` 7/7 PASS、`test:runtime-up` 30/30 PASS、実PostgreSQLの
  Connector lifecycle PASS、`git diff --check` PASS。実装commit `9d6a6d51f`。
