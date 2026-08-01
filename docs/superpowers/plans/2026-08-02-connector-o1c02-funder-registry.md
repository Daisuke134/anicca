# O1C-02 funder registry 再構築計画

**Goal:** 分散したlegacy portfolioとfunder specsを、tenant-bound・append-only・再検証前提の一つのregistryへ変換する。

## Contract

- portfolioとspecのID setが完全一致する場合だけimportする。
- official URL、type、priority、known automation blockerを正規化する。
- legacyのamount/deadline/verifiedはcurrent factへ昇格せず`stale_claim`として保持する。
- current verificationは全件`needs_reverification`から始め、O1C-15の当日検証前にsubmit-readyにしない。
- revision digest付きsnapshotをappend-only tenant tableへ保存する。

## Steps

1. set mismatch、stale claim、blocker分類、append-only storeをRED testで固定する。
2. registry builder、store、migrationを実装する。
3. 実legacy 5件をprivacy-safeにimport readbackする。
4. 全回帰、evidence、spec、残数、commit/pushを完了する。
