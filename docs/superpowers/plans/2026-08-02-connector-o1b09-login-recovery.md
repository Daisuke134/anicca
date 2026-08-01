# Connector O1B-09 Login Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 旧ConnectorのLuma login知識を、既存CloakBrowser daily-driverを使う正本events packへ統合し、login切れを人の操作なしで一度だけ復旧して同じeventを再検査する。

**Architecture:** 第二browser、第二runtime、cookie export、手動OTPを作らない。既存`:9222`共有context内でLuma authを検査し、必要な場合だけ既存Google sessionを使ってsign-inするsingle-flight recoveryを追加する。Luma providerは`login_required`時に一度だけrecoveryを呼び、同じcontractをfresh pageで再検査する。復旧できなければ成功を偽装せず`login_required`のまま止める。

## Constraints

- browser全体と既存tabを閉じず、自分で作ったpageだけを閉じる。
- Google account、cookie、token、mail本文をlog、receipt、evidenceへ保存しない。
- registration submit後は認証retryしない。unknown effectを優先して二重応募を防ぐ。
- recoveryは同時要求を一つへまとめ、各provider operationにつき最大一回に固定する。
- live検証は現在の認証を壊さずread-onlyで行う。logoutして障害を人工的に作らない。

### Task 1: Recovery contract (TDD)

- [x] 認証済みならGoogle操作なしでsafe metadataだけを返すREDを追加。
- [x] login切れならGoogle sign-inを一度だけ行い、認証後readbackが取れた時だけ成功するREDを追加。
- [x] 同時要求のsingle-flight、失敗時fail-closed、既存page ownershipのREDを追加。
- [x] 最小実装でfocused testをGREENにする。

### Task 2: Events pack wiring (TDD)

- [x] providerが`login_required`を見た時だけrecoveryを一回呼び、same contractを再検査するREDを追加。
- [x] recovery失敗、再検査もlogin、submit後unknown effectでretryしない境界を固定する。
- [x] `runtime-up` production wiringとConnector compose envを追加する。
- [x] outbound、runtime-up、browser-auth回帰をGREENにする。

### Task 3: Live read-only proof and SSOT

- [x] 実`:9222`で認証済みreadback、共有context 1、既存page count不変を確認する。
- [x] secretなしevidence JSONを追加する。
- [x] O1B-09を完了へ更新し、残数を再計算する。
- [ ] commitしてfeature branchをpushする。
