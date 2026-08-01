# Connector O1B-10 Legacy Event Loop Retirement Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** event discovery・応募・日報の外部操作ownerをLife Manager正本runtimeへ一本化し、旧Connectorと旧meetup/connpass経路を再起動可能な形で退役する。

**Architecture:** sourceや過去stateは削除しない。正本repoにexact allowlistのretirement commandを置き、launchd 2件はbootout後にplistを`.retired`へ移動、OpenClawの重複cronはexact IDでdisableする。複合`anicca-night-fill`も削除せずdisabledを維持する。適用前後をmachine-readable inventoryで検証する。

## Constraints

- glob、部分一致、全cron一括変更を使わない。
- 旧source、ledger、evidence、Calendar eventは削除しない。
- `outbound.event.apply` workerとGuardianは停止しない。
- connpassはO1B-11のAPI key取得まで全自動アクセスを止める。
- rollbackは`.retired` plistの復元とexact cron enableで可能にする。

### Task 1: Exact retirement contract (TDD)

- [x] 退役対象launchd/cron、保持対象をpure manifestで固定する。
- [x] 不明target、曖昧ID、plist衝突はfail closedする。
- [x] dry-run inventoryと適用結果検証を実装する。

### Task 2: Apply to live legacy runtime

- [x] 適用直前inventoryをsecretなしで保存する。
- [x] exact targetだけを退役し、source/stateは保持する。
- [x] launchd print、OpenClaw cron readback、正本worker healthでpostconditionを確認する。

### Task 3: SSOT and delivery

- [x] O1B-10完了、残数127件へspecを更新する。
- [x] focused/full回帰とdiff checkを通す。
- [ ] evidenceをcommitし、累積feature branchへpushする。
