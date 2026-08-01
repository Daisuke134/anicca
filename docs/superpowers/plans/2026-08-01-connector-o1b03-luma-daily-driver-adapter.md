# Connector O1B-03 Luma Daily-Driver Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> Status: 実行中。O1B-04の実イベント登録はまだ行わない。

**Goal:** 既存の唯一のCloakBrowser daily-driver `http://127.0.0.1:9222`を共有transportとして使い、Lumaの東京対面event探索と証拠付きRSVPを既存`outbound.event.apply` runtime adapterへ接続する。

**Architecture:** 第二browser、第二queue、別runtimeを作らない。agentがLuma inventoryとevent本文を読み、codeはCDP owner・tenant・effect fence・証拠境界だけを固定する。adapterは`plan / execute / reconcile / verify / report`契約を実装し、submit直前に同じjob/attemptのeffect fenceを確認する。submit後はE1/E2/E3が揃った場合だけverified receiptを返し、不明な外部効果は`unknownEffect=true`でreconciliationへ送る。

**Tech Stack:** Node.js 20、Playwright CDP、CloakBrowser daily-driver `:9222`、既存runtime adapter registry、node:test。

## Constraints

- Luma APIは主催者向けのため参加者RSVPには使わない。
- Steel、CamoFox、別Chrome `:9223`を新規transportとして使わない。
- 共有contextや既存tabを閉じず、自分で開いたpageだけを閉じる。
- cookie、magic link、guest key、email、住所をjob payload・log・specへ保存しない。
- O1B-03ではfixture/E2E-read-onlyまで。実イベントへの不可逆submitはO1B-04で一度だけ行う。
- 正本specをRED、GREEN、commit、pushごとに更新する。

---

### Task 1: Daily-driver read-only contract

- [x] `:9222` owner、共有context、Luma login状態をsecretなしでread-only実測する。
- [x] CDP接続、origin allowlist、自分のpageだけをcloseするtransport testをRED→GREENにする。
- [x] login切れは失敗偽装せず、既存Google/Luma認証復旧へ分類する。
- [x] Commit and push.

### Task 2: Luma discovery contract

- [x] 東京・対面inventoryをscroll/pagination終端まで読むfixtureを作る。
- [x] event URL、日時、場所、定員、RSVP状態をreference-only candidateへ変換する。
- [x] category hard filterを置かず、agent判断用の本文を保持する。
- [ ] 同日次候補へ進める失敗分類を実装する。
- [ ] Commit and push.

### Task 3: RSVP adapter and effect fence

- [ ] `outbound.event.apply` adapter契約のRED testsを書く。
- [ ] submit前effect fence、登録済みreconcile、login/full/approval/failed分類を実装する。
- [ ] E1/E2/E3 verifier由来receiptだけをruntime completionへ返す。
- [ ] production manifestとworker servicesへportableに登録する。
- [ ] runtime/outbound/adapter回帰を通す。
- [ ] Commit and push.

### Task 4: O1B-03 evidence and handoff

- [ ] read-only live Luma pageとproduction registry wiringを検証する。
- [ ] secretなしevidence JSONを保存する。
- [ ] O1B-03を完了にし、実submit O1B-04を次にする。
- [ ] Commit and push.
