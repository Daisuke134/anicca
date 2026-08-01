# Connector O1B-18 preference ranking 実装plan

1. verified date inventoryだけを受けるranking contractをtest先行で定義する。
2. 全event refのexact permutation、fit enum、bounded reason、immutable provenanceを実装する。
3. Gemini strict JSON requestを実装し、untrusted event dataと自然言語preferencesを分離する。
4. model failure、invalid JSON、欠落、重複、未知refにfallbackしないtestを通す。
5. 実Gemini evalを複数fixtureで実行し、候補保持率100%を確認する。
6. `test:outbound`へ登録し、全回帰を実行する。
7. evidenceとmaster specを更新し、commit/pushする。

