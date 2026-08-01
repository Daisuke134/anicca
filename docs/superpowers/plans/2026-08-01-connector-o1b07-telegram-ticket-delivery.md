# Connector O1B-07 Telegram Ticket Delivery Implementation Plan

> Status: 実行中。O1B-06のverified QR artifactだけをDaisへ一度送る。

**Goal:** `Engineer BAR`の公式QR PNGを、event名・日時・会場・選定理由・event/Calendar直接linkと一緒に既存OpenClaw Telegram transportで実送信し、positive message IDをreceiptへ保存する。

## Constraints

- 新しいTelegram botやtransportを作らず、稼働中OpenClaw Telegram accountと既存targetを使う。
- Telegramには技術語、runner、job ID、hash、guest keyを表示しない。
- linkはbutton placeholderではなく、Telegramから直接tapできる実URLにする。
- QRはO1B-06のtenant-bound artifactから読み、別画像やbase64 JSONを送らない。
- `ok`だけでは成功にせず、positive Telegram message IDを必須にする。
- bot token、chat ID、guest keyをlog、spec、evidence、receiptへ平文保存しない。

### Task 1: Human-readable report contract

- [ ] exact event dataから日本語captionと直接linkを組み立てるtestをRED→GREENにする。
- [ ] placeholder、技術語、secret、未実装linkを拒否する。

### Task 2: Existing OpenClaw delivery

- [ ] runtime volumeのverified QRを読み、0600 temporary PNGだけをOpenClawへ渡す。
- [ ] 実Telegramへ一度送信し、positive message IDを検証する。
- [ ] chat IDはSHA-256だけをreceiptへ残す。

### Task 3: Proof and handoff

- [ ] secretなしlive evidenceを保存する。
- [ ] O1B-07完了、spec更新、commit、push。
- [ ] O1B-08へ進む。
