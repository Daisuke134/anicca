# Connector O1B-20 source handoff 実装plan

1. Luma candidate outcomeへin-process provenanceを追加する。
2. Luma/connpass capability matrixをsecret値非保持で実装する。
3. verified exhaustionだけを受けるsource handoffをtest先行で定義する。
4. keyなしはnetwork 0 + open + key watcher/Luma retry、keyありは公式GET discoveryだけを実装する。
5. connpass候補をadvisory-onlyに正規化し、coverageへ昇格できないtestを追加する。
6. events pack/runtime境界へhandoffを接続する。
7. 実secret/Gmail状態、outbound全回帰、evidence、master specを更新しcommit/pushする。

