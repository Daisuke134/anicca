# O1B-25 Telegram coverage summary 実装計画

**Goal:** 21日coverage、既存予定、新規予約、open、申込証拠、選定理由を非技術者が読める一通のTelegramへまとめ、positive message IDで配信を証明する。

## Contract

- exact 21日coverageとcounts整合を検証する。
- 全`covered_new`日へ同日reservation、provider receipt、選定理由を1:1で要求する。
- 21日すべてを一通の4096文字以内messageへ表現する。
- send callは一回だけで、positive message IDだけをdelivery receiptにする。
- raw chat ID、event title、選定理由をdelivery receiptへ保存しない。

## Steps

1. 21日表示、reservation 1:1、one-send、message ID gateをRED testで固定する。
2. summary builderとOpenClaw deliveryを実装する。
3. controlled deliveryと、可能なら既存Dais targetへのtruthful live summaryを実行する。
4. 全回帰、evidence、spec、残数、commit/pushを完了する。
