# Connector O1B-09 Existing Login and Events Pack Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

> Status: 実装中。

**Goal:** O1B-04で実証したDaisのLuma email-code認証復旧を再利用可能な正規componentにし、既存CloakBrowser daily-driver、Luma discovery、`outbound.event.apply`を一つのConnector events packとして接続する。

**Architecture:** 第二browser、第二queue、第二schedulerを作らない。正本`life-manager`だけがpackを所有し、既存`:9222` shared contextを使う。各passは最初に認証状態をread-only確認し、login切れの場合だけ同じpageでemail codeを要求し、既存`gog` Gmail OAuthからrequest後の新着codeを取得して入力する。認証確認後だけ既存discover/inspect/applyへ戻る。code、cookie、mail本文、account tokenは保存・出力しない。

## Constraints

- `/Users/anicca/profitable-claude`は棚卸し元に限定し、編集・runtime依存・commit対象にしない。
- 旧`anicca-booking`の`PROPOSED`先行、Slack報告、CamoFox優先、hard category filterは移植しない。
- 既存のCalendar全page scan、同一daily-driver、Gmail OAuth、登録後証拠という有用な境界だけを統合する。
- 認証復旧は外部応募effect開始前にだけ行う。応募後の不明状態を認証retryで再送しない。
- O1B-09はlogin/events pack統合まで。21日coverageとsource fallbackはO1B-16以降で実装する。
- 正本specをRED、GREEN、live verification、commit、pushごとに更新する。

### Task 1: Inventory and pack contract

- [x] 旧Connector、`anicca-booking`、O1B-03〜08の重複と採用境界を表にする。
- [x] 認証済み、復旧成功、復旧不能、応募effect開始後の4経路をRED testで固定する。
- [x] events packの唯一のproduction composition surfaceを追加する。
- [ ] Commit and push.

### Task 2: Gmail-backed daily-driver recovery

- [x] O1B-04のemail-code flowをsecret非出力componentへ移す。
- [ ] request開始時刻より古いmail、別sender、別account、6桁でないcodeを拒否する。
- [ ] 同じdaily-driver pageでcode入力後、authenticated markerを再読出しする。
- [ ] focused testとoutbound regressionを通す。
- [ ] Commit and push.

### Task 3: Runtime integration

- [ ] packを既存`outbound.event.apply` production compositionへ接続する。
- [ ] login切れなら一回だけ復旧してinspect/applyへ戻り、復旧不能ならsubmit前failureにする。
- [ ] worker health、runtime adapter、effect fenceの回帰を通す。
- [ ] Commit and push.

### Task 4: Live verification and evidence

- [ ] 現在の`:9222` Dais Luma sessionをsecretなしでread-only確認する。
- [ ] pack経由でLuma Tokyo inventoryまたは既存event detailを読み、同じ認証contextを使ったことを確認する。
- [ ] secretなしevidence JSONを保存する。
- [ ] O1B-09を完了にし、O1B-10の旧実装退役へ進む。
- [ ] Commit and push.
