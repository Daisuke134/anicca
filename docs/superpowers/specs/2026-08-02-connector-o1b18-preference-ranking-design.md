# Connector O1B-18 preference ranking設計

status: APPROVED
owner: Connector
date: 2026-08-02 JST

## 目的

AI、crypto、英語、founder等の好みを候補の順位にだけ反映し、それ以外の東京対面eventを
候補集合から捨てない。

## 採用設計

- 入力はO1B-17が作ったverifiedなLuma日付別inventory snapshotと対象日、自然言語の好みである。
- semanticな適合度と理由はGeminiが判断する。keyword、regex、固定category scoreへfallbackしない。
- modelは対象日の全`event_ref`をexactly onceで返す。array順が優先順位である。
- 各候補には`strong / moderate / weak / unknown`のpreference fitと人間向け理由を付ける。
- `weak`と`unknown`も候補に残す。schemaに`eligible`、`exclude`、`discard`を持たせない。
- 欠落、重複、未知ref、追加field、invalid JSON、model failureはfail closedする。
- 0候補日はmodelを呼ばず、verifiedな空rankingを返す。ただしcoverageは`open`のままにする。

## O1B-19との境界

O1B-18は候補を減らさないpreference orderingだけを所有する。event本文、主催者、参加者、場所、
時間、Daisの目標、serendipityを根拠付きで評価するのはO1B-19である。

## 完了条件

1. deterministic validatorが全候補のexact permutationを強制する。
2. model promptが好みはorderingだけであり除外禁止と明示する。
3. model failure時にkeyword fallbackがない。
4. 複数の好みと非好み候補を含む実Gemini evalで、全候補保持と期待する上位傾向を実証する。
5. outbound全回帰、証拠、spec、commit、pushが揃う。

