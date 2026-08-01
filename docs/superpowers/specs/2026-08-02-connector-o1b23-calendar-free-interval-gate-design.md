# Connector O1B-23 全Calendar free interval gate 設計

## 実測

- 既存`gog` account/keyring認証は利用可能。追加credentialは不要。
- Google Calendarは5個。
- 2026-08-02〜2026-08-22の全calendarには124 event、eventを持つcalendarは3個。
- 予定本文・個人identity・credential値は証拠へ保存しない。

## 目的

主calendarだけでなく全calendarの予定を読み、event開始前の移動と終了後の移動を含めて衝突しない候補だけを申込可能にする。

## データ境界

1. `gog calendar calendars -j --all --no-input`でcalendar listを全page取得する。
2. `gog calendar events --all -j --all-pages --from --to --no-input`でrolling 21日を全page取得する。
3. cancelledとfree/transparentをbusyにしない。timed eventとall-day eventを別形式から正規化する。
4. normalized intervalはcalendar/eventのopaque ref、開始、終了、busy statusだけを持つ。
5. calendar listまたはeventsの終端を証明できなければfail closedする。

## 申込前gate

- 候補ごとに現在地→会場の到着所要時間と、会場→次予定/帰宅地点の所要時間を既存route transportで求める。
- `[event start - inbound travel, event end + outbound travel]`が全busy intervalと交差しない時だけeligible。
- 一件衝突しても同日の別時間・別候補へ進む。
- 短い既存予定が一件あるだけで一日全体を`covered_existing`または`unavailable`にしない。
- `unavailable`は同日全候補についてcalendar event ref付き衝突証拠が揃った時だけ作る。
- route不能やcalendar不完全を`unavailable`へ変換せずrecoveryへ送る。

## Calendar書込み

verified Luma registration後だけ、canonical event URL、開始終了、会場、provider receipt refをGoogle Calendarへ反映する。同一provider eventの再実行は重複作成しない。

## 完了条件

全calendar/全page provenance、移動込み候補gate、短い予定の前後へ候補を残すこと、衝突時の次候補継続、verified登録後のCalendar idempotencyをtestと実read-only runで確認する。
