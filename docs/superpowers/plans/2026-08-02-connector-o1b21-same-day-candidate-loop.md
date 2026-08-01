# O1B-21 same-day candidate continuation 実装計画

**Goal:** 一候補の既知の申込失敗・満席・不適格で日次処理を終えず、同じ日の次候補へ進み、検証済み予約receiptを得た時だけ完了する。

## Contract

- loopへ対象日を明示し、全候補の`event_date`がその日と一致することを入口で検証する。
- effect開始前に確定した`application_failed / full / not_eligible`はskip ledgerへ残して次候補へ進む。
- `verified_registered`かつ正規provider receiptだけを`booked`にする。
- login・transport・inventory不備はrecovery、unknown effectはreconciliationで止める。
- 候補を尽くした場合だけ次providerへ渡す。

## Steps

1. 同日境界、既知申込失敗からの継続、verified receiptまでの順序をRED testで固定する。
2. candidate sequenceとprovider routerへ対象日を接続する。
3. focused / outbound / runtime回帰を実行する。
4. controlled readback、evidence、spec、残数、commit/pushを完了する。
