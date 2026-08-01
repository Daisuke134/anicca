# O1B-24 event spend policy 実装計画

**Goal:** 無料eventを常に先に処理し、有料eventは保存済み自動支出policyと決済参照の範囲内だけを都度承認なしで実行可能にする。

## Contract

- 既存priority内の相対順を保ちながら無料候補を有料候補より先にする。
- 有料候補はpolicy ref、saved payment method ref、currency、per-event上限、rolling残額を全て検証する。
- policy内は`approval_required=false`のtyped purchase decisionを作る。
- policy外、currency不一致、決済参照なしは自動拒否し、人への都度承認へ変換しない。
- rolling残額は同一plan内の先行authorized eventを差し引く。

## Steps

1. 無料優先、policy内自動購入、上限超過、決済参照欠落をRED testで固定する。
2. deterministic event spend plannerを実装する。
3. controlled mixed-price readbackと全回帰を実行する。
4. evidence、spec、残数、commit/pushを完了する。
