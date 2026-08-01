# Connector O1B-04 Live Luma Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

> Status: 実行中。実イベント一件のverified registrationだけをこのsliceで成立させる。

**Goal:** 既存CloakBrowser daily-driver上の`keiodaisuke@gmail.com` Luma認証を自動復旧し、Google Calendarと競合しない東京対面event一件へ既存`outbound.event.apply` workerで登録する。

**Architecture:** 第二browser、第二queue、手動OTP、偽receiptを作らない。同じ`:9222` profileでLuma email codeを要求し、既存`gog` Gmail OAuthで新着codeだけを読み、同じpageへ入力する。登録はO1B-03 adapterを一度だけ実行し、E1 provider response、E2 PNG、E3 canonical URLを同一attemptで検証する。

## Constraints

- 登録前にGoogle Calendarの対象時間と移動余白を読む。
- Luma inventoryを最後まで読み、category hard filterを使わない。
- Luma上で即時決済が必要な有料ticket、online、満席、waitlist、承認制、競合は登録せず次candidateへ進む。現地払いだけでLuma登録時の支出が0なら候補にできる。
- code、cookie、mail本文、Google tokenをlog・spec・job・evidenceへ保存しない。
- browser全体や既存tabを閉じず、自分のpageだけを閉じる。
- 成功はverified receipt、登録後readback、canonical URLの一致でのみ確定する。

### Task 1: Existing-account authentication

- [x] 新しいLuma sign-in codeを同じdaily-driverから要求する。
- [x] `gog`でrequest後の新着Luma mailだけを読み、codeを出力せず入力する。
- [x] authenticated readbackを確認する。
- [x] spec更新、commit、push。

### Task 2: Conflict-free live candidate

- [x] rolling horizonのGoogle Calendarを全page取得する。
- [x] 東京対面Luma inventoryを終端まで取得する。
- [x] 競合・移動不能・即時決済・満席等を除外し、登録可能candidateをagentが本文から選ぶ。
- [x] spec更新、commit、push。

### Task 3: One verified registration

- [ ] durable jobをenqueueし、production workerに一度だけclaimさせる。
- [ ] E1/E2/E3 verified receiptと登録後readbackを照合する。
- [ ] secretなしlive evidenceを保存する。
- [ ] O1B-04完了、spec更新、commit、push。
