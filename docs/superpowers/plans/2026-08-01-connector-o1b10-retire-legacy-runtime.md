# Connector O1B-10 Retire Legacy Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

> Status: 実装中。

**Goal:** `profitable-claude`の旧Connector fill-gapsと旧Telegram日報を停止し、正本`life-manager`のevents pack、durable worker、Guardianだけを実行系として残す。

**Architecture:** 旧code repositoryは削除せずreference-only archiveとして残す。固定allowlistの2 launchd labelだけをbootout + disableし、plistをowner-only state archiveへ移動する。正規Guardianや他loopには触れない。操作はidempotentかつmanifest/checksum付きで、必要なら`launchctl enable`とplist復元で戻せる。

## Constraints

- 対象は`ai.anicca.connector-fill-gaps`と`ai.anicca.connector-daily-report`だけ。
- `ai.anicca.outbound-runtime-healthcheck`、Docker worker、PostgreSQL、runtime volumeは停止・削除しない。
- `/Users/anicca/profitable-claude`のdirty worktreeを編集・commitしない。
- 旧plistを永久削除せず、`~/.local/state/life-manager/retired-launchd/o1b10/`へ移動する。
- disabled state、archive、checksum、正規Guardian healthを実測する。
- 正本specを各checkpointで更新し、commit/pushする。

### Task 1: Deterministic retirement contract

- [x] 固定2 label以外を拒否し、dry fixtureでbootout/disable/archiveをRED→GREENにする。
- [x] 二回目実行が成功し、archiveを上書きしないidempotencyを確認する。
- [x] rollback手順をmanifestへ残す。
- [x] Commit and push.

### Task 2: Prevent resurrection

- [x] 旧launchd inventory/reconcilerがplistを再生成する経路を確認する。
- [x] 正本側tombstoneまたは旧inventoryの安全な変更で2 labelの再登録を防ぐ。
- [x] 他legacy job classification回帰を通す。
- [x] Commit and push.

### Task 3: Live retirement and verification

- [ ] 実2 labelをbootout + disableし、plistをowner-only archiveへ移す。
- [ ] `launchctl print`不在、original plist不在、archive/checksum、disabled stateを確認する。
- [ ] 正規Guardian launchd、worker health、events pack live read-onlyが正常なことを確認する。
- [ ] secretなしevidence JSONを保存しO1B-10を完了する。
- [ ] Commit and push.
