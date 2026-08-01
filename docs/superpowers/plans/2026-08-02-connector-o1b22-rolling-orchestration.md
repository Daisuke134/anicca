# O1B-22 rolling orchestration 実装計画

**Goal:** 一巡・一候補・一sourceの局所結果を21日coverage全体の終了へ誤変換せず、証拠付きopen 0だけを終了条件にする。

## Contract

- 入力はO1B-16のexact 21日coverageとし、`open`の日だけを一巡する。
- 一日のoperation例外、recovery、reconciliation、provider枯渇はその日をopenに残し、後続日を処理する。
- 正規provider receipt付き`booked`だけをその日の新規coverageとして数える。
- 一巡後にopenが残れば必ず`continue_required`と次runを要求する。
- 初期または処理後のopen 0だけを`complete`にする。

## Steps

1. 局所失敗後の後続日継続、一巡非終了、receipt gateをRED testで固定する。
2. deterministic rolling orchestratorを実装する。
3. controlled 3日readbackと全回帰を実行する。
4. evidence、spec、残数、commit/pushを完了する。
