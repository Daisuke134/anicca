# Connector O1A-06 Live Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> Status: 完了。実装commit `a7c01157e`、`df1ac3495`、`43d9134fc`。live evidenceは`docs/evidence/outbound/2026-08-01-o1a06-live-recovery.json`。

**Goal:** Connector runtime workerの実停止をGuardianが検知し、DaisへTelegram警告を届け、自動再起動し、復旧通知まで実message ID付きで証明する。

**Architecture:** O1A-05の`/health`判定を維持し、異常時は既存OpenClaw Telegram transportへ警告を送り、local Docker workerを再起動してboundedにhealthを再確認する。復旧できない場合だけ既存`self-fix.sh`へ昇格する。通知receiptとincident stateはlocal runtime stateへ保存し、同じincidentの警告spamを防ぐ。

**Tech Stack:** Node.js 20、OpenClaw CLI、Docker Compose、launchd、node:test。

## Global Constraints

- O1A-06だけを実行し、O1Bへ進まない。
- 応募判断はagentに残し、GuardianはHTTP・role・capability・poll時刻・message IDだけを決定論的に扱う。
- Telegram送信成功はpositive message IDでのみ成立する。
- 既存Honne JA shadow設定とDocker volumeを保存する。
- ユーザー所有の未コミットファイルを変更・stageしない。
- 正本specを着手、RED、GREEN、実機証拠、完了の各段階で更新してpushする。

---

### Task 1: Telegram incident contract

**Files:**
- Modify: `apps/life-manager/lib/outbound-guardian.test.js`
- Modify: `apps/life-manager/lib/outbound-guardian.js`

**Interfaces:**
- Consumes: `runOutboundGuardian(options)`、既存health verdict。
- Produces: `notifyIncident(message)`、positive message ID、incident receipt、recovery result。

- [x] **Step 1: Write the failing tests**

  異常時に非技術的な停止警告を一度送り、positive message IDを保存してからrecoveryを実行する。同じincidentは再通知しない。復旧時に復旧通知を送り、positive message ID取得後だけincidentをclearする。message ID欠落は送信成功にしない。

- [x] **Step 2: Run test to verify it fails**

  Run: `node --test lib/outbound-guardian.test.js`
  Expected: notification/recovery contractが未実装のためFAIL。

- [x] **Step 3: Write minimal implementation**

  既存`openclaw message send --channel telegram --target <local target> --message <copy> --json`を呼び、`messageId`を検証する。local incident JSONをatomic renameで保存する。

- [x] **Step 4: Run tests to verify GREEN**

  Run: `npm run test:outbound && npm run test:runtime-up`
  Expected: 0 failures。

- [x] **Step 5: Commit and push**

  Commit notification/recovery implementation only, then push `main`。

### Task 2: Reproducible launchd and local recovery wiring

**Files:**
- Modify: `skills/self/outbound-runtime-healthcheck.sh`
- Modify: `skills/self/launchd/ai.anicca.outbound-runtime-healthcheck.plist`
- Modify: `skills/self/install-outbound-runtime-healthcheck-launchd.sh`
- Create: `deploy/local/compose.connector.yaml`

**Interfaces:**
- Consumes: local Telegram target、worker container name、existing compose project。
- Produces: installed launchd job and worker health port `127.0.0.1:18790`。

- [x] **Step 1: Add failing static/runtime tests**

  installer renderはTelegram targetを必須とし、render済みplistへtarget、container、health URLが入ることを要求する。Connector overlayは`outbound.event.apply`をworker capabilityへ追加する。

- [x] **Step 2: Verify RED**

  Run installer/static test before implementation and confirm the missing arguments/config fail。

- [x] **Step 3: Implement minimal wiring**

  launchd wrapperは`~/.openclaw/.env`をsourceし、plistからtarget/containerを受ける。compose overlayはcapabilityだけを上書きし、既存Honne overrideを最後まで保持する。

- [x] **Step 4: Verify GREEN**

  Run `plutil -lint`、`bash -n`、`docker compose ... config --quiet` and targeted Node tests。

- [x] **Step 5: Commit and push**

  Commit wiring only, then push `main`。

### Task 3: Real stop-alert-recover proof

**Files:**
- Create: `docs/evidence/outbound/2026-08-01-o1a06-live-recovery.json`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

**Interfaces:**
- Consumes: installed launchd job、running local worker、Telegram target。
- Produces: before/alert/recovery health observations、Telegram message IDs、launchd state、timestamps。

- [x] **Step 1: Deploy without losing existing state**

  Rebuild only current runtime services using base compose + existing Honne shadow override + Connector overlay. Verify worker health includes `outbound.event.apply` and fresh `last_poll_at`。

- [x] **Step 2: Install and verify Guardian**

  Install the launchd plist with the local Dais Telegram target. Kick once while healthy and prove no false alert。

- [x] **Step 3: Force one real stop**

  Stop exactly `life-manager-local-worker-1`, immediately run Guardian, and capture the unhealthy verdict and alert message ID。

- [x] **Step 4: Verify autonomous recovery**

  Prove the worker container is running, `/health` is 200 with fresh poll, recovery Telegram has a positive message ID, and incident state is cleared。

- [x] **Step 5: Record and verify evidence**

  Write only non-secret evidence, run JSON parse validation, targeted tests, `launchctl print`, `/health`, and local/remote git equality checks。

- [x] **Step 6: Update canonical spec, commit, and push**

  Mark O1A-06 complete only when every live proof exists. Otherwise leave it unchecked with the exact failed gate.
