# Connector O1A-03 Evidence Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** events・funders・jobsが「応募完了」を名乗る前に、E1外部確認、E2実PNG、E3 canonical URLの三証拠を同じattemptへ結合して検証する共通moduleを作る。

**Architecture:** callerが渡す`verified=true`等の自己申告は信用しない。E1は外部receipt reader、E2はimmutable object reader、E3はHEAD requestを共通gate自身が呼ぶ。三つを独立に検証し、全部揃った時だけ`status=verified`と安定evidence hashを返し、一つでも欠ければ`status=failed`と欠落tierを返す。

**Tech Stack:** Node.js 20、CommonJS、`node:test`、既存`object://sha256/` content reference

## Global Constraints

- 正本は`docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`。
- 実装順はO1A→O1B→O1C→Order 2→3A→3B→4→5→Webから変更しない。
- 成功は`E1 AND E2 AND E3`のみ。DOM文字列、callerのboolean、自作テキストで成功を宣言しない。
- E1は`provider-receipt://`、`gmail-message://`、`ticket://`のrepository外referenceだけを受ける。
- E2は`object://sha256/<64 hex>`の実bytesを読み、PNG magic number、5000 bytes以上、reference hash一致を検証する。
- E3はHTTPS URLへ`HEAD`、`redirect=manual`で実測し、status 200だけを認める。`/join/complete/`を含む一回性URLは禁止する。
- event評価や成功文言の判断をhardcodeしない。ここは外部I/O、format、hash、bookkeepingだけを扱う。
- production codeより先に失敗testを実行し、commit前にfresh verificationを実行する。
- ユーザーの明示指示により既存`main`で連続実行し、対象ファイルだけをcommit・pushする。

---

### Task 1: Shared E1/E2/E3 gate

**Files:**
- Create: `apps/life-manager/lib/outbound-evidence.js`
- Create: `apps/life-manager/lib/outbound-evidence.test.js`
- Modify: `apps/life-manager/package.json`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

**Interfaces:**
- Consumes: `verifyOutboundEvidence(input, dependencies)` with `tenantId`、`attemptRef`、`externalReceiptRef`、`artifactRef`、`canonicalUrl`
- Dependencies: `readExternalReceipt(tenantId, ref)`、`readArtifact(tenantId, ref)`、`fetchImpl(url, {method:"HEAD", redirect:"manual"})`
- Produces: immutable `{status:"verified"|"failed", attempt_ref, missing, evidence, evidence_hash}` without raw mail, screenshot bytes, cookies, or credentials.

- [x] **Step 1: failing contract testsを書く**

  実PNG signatureを持つ5000 bytes fixtureと手計算したSHA-256 object refを使い、三証拠が揃うとverifiedになるtestを書く。E1 reader失敗、E2が4999 bytes、E3が302、`/join/complete/` URLの各caseはfailedとなり、欠落tierが正確であることを書く。raw email、file path、HTTP URLは拒否する。

- [x] **Step 2: REDを確認する**

  Run: `node --test lib/outbound-evidence.test.js`

  Expected: `Cannot find module './outbound-evidence.js'`でFAIL。

- [x] **Step 3: 最小実装を書く**

  fixed reference/URL formatをparseし、E1/E2/E3を個別に`try/catch`する。PNG bytesは先頭8 bytesとsizeとSHA-256を検証する。HEADはtimeout signalをcallerから注入せず`AbortSignal.timeout(30000)`でboundedにする。結果は固定key順でSHA-256し、raw evidenceを返さない。

- [x] **Step 4: GREENと回帰testを確認する**

  Run: `node --test lib/outbound-evidence.test.js lib/outbound-event-job.test.js lib/runtime-lease-heartbeat.test.js`

  Expected: 全test PASS、warning/errorなし。

- [ ] **Step 5: package・spec・verificationを閉じる**

  `test:outbound`へ新testを追加し、O1A-03を完了へ変更する。Run: `npm run test:outbound && npm run test:runtime-up && git diff --check`。全command exit 0後、対象ファイルとplan/specだけをcommitし、`origin/main`へpushしてlocal/remote hashを一致させる。
