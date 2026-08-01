# Connector O1B-21 同日候補継続 loop 設計

## 目的

一件の申込結果を一日の終了条件にせず、同じ日の順序付きLuma候補をverified registrationまで処理する。

## 境界

- 既存`runLumaCandidateSequence`を唯一の候補継続state machineとする。
- events packがこのstate machineを公開し、別のhost loopを作らない。
- `full / waitlist / approval_required / not_eligible / conflict / cancelled`は次候補へ進む。
- `login_required / transport_unavailable / inventory_incomplete`は候補を消費せず復旧へ移す。
- `unknown_effect / unverified_result`は二重申込を避けreconciliationへ移す。
- verifier由来のprovider receiptを伴う`verified_registered`だけを`booked`にする。
- 全候補を使い切った時だけ、同日を次sourceへhandoffする。

## 完了条件

events packから同日候補loopを呼べること、clone/fake resultをhandoffへ渡せないこと、focused/full regressionが成功すること。
