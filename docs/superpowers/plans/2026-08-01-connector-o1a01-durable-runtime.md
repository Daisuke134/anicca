# Connector O1A-01 Durable Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connectorのevent applicationを、既存の`lm_runtime_jobs`へ秘密値なし・idempotentにenqueueできるjob contractとして接続する。

**Architecture:** 新しいoutbound queueは作らず、既存の`runtime-job-store.js`を唯一のdurable runtimeとして再利用する。今回のsliceはevent applicationのimmutable referenceとjob/effect keyを構築してenqueueするところまでとし、CloakBrowserによるLuma実操作はO1A-02以降のexecutor adapterで行う。

**Tech Stack:** Node.js 20、CommonJS、`node:test`、既存`lm_runtime_jobs` PostgreSQL protocol

## Global Constraints

- 正本は`docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`。
- 実装順はO1A→O1B→O1C→Order 2→3A→3B→4→5→Webから変更しない。
- 新しいqueue、browser、secret storeを作らない。
- job payloadにはsecret、氏名、メール、電話、cookieを保存せず、repository外のreferenceだけを保存する。
- event applicationは外部状態を作るため`effect_class=publish`とし、同一tenant・同一event・同一identityの重複申込をeffect keyで防ぐ。
- production codeより先に失敗testを実行し、完了主張とcommit前にfresh verificationを実行する。

---

### Task 1: Event application job contract

**Files:**
- Create: `apps/life-manager/lib/outbound-event-job.js`
- Create: `apps/life-manager/lib/outbound-event-job.test.js`
- Modify: `apps/life-manager/package.json`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

**Interfaces:**
- Consumes: `buildRuntimeJob(input)`と`enqueueJob(input, opts)` from `apps/life-manager/lib/runtime-job-store.js`
- Produces: `buildEventApplicationJob(input)`、`enqueueEventApplication(input, opts)`、`CAPABILITY="outbound.event.apply"`、`LOOP_ID="outbound.events"`

- [ ] **Step 1: failing contract testを書く**

  `outbound-event-job.test.js`で、Luma event URL、start ISO、`identity://`、`browser-profile://`から、secretを含まないreference-only jobが作られること、同じ入力が同じjob/effect keyになること、異なるeventは異なるkeyになること、raw identityを拒否すること、injected `enqueueJob`へ正確なjobを渡すことを検証する。

- [ ] **Step 2: REDを確認する**

  Run: `node --test lib/outbound-event-job.test.js`

  Expected: `Cannot find module './outbound-event-job.js'`でFAIL。

- [ ] **Step 3: 最小実装を書く**

  `outbound-event-job.js`へ、canonical Luma URLのslug抽出、ISO検証、許可されたreference scheme検証、SHA-256による安定job/effect key、既存storeへのenqueueだけを実装する。browser操作、Calendar、Telegram、候補rankingは入れない。

- [ ] **Step 4: GREENと回帰testを確認する**

  Run: `node --test lib/outbound-event-job.test.js lib/runtime-job-store.test.js`

  Expected: 全test PASS、warning/errorなし。

- [ ] **Step 5: package testと正本仕様を更新する**

  `test:outbound`へ新testを追加する。仕様のO1A-01を「既存`lm_runtime_jobs`を唯一のruntimeとしてevent application job contractへ接続」に修正し、実test結果とcommit evidenceを記録してcheckboxを完了にする。

- [ ] **Step 6: 全verification後にcommit・pushする**

  Run: `npm run test:outbound && git diff --check`

  Expected: exit 0。その後、対象4ファイルとplan/specだけをcommitし、`origin/main`へpushしてlocal/remote hash一致を確認する。
