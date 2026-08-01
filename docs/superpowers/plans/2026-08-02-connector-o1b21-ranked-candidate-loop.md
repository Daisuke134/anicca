# Connector O1B-21 実装plan

1. events packが候補sequenceを公開する契約testを追加する。
2. 既存verified candidate state machineだけへ接続する。
3. 次候補、復旧、reconciliation、全候補exhaustionをfocused testで再検証する。
4. source handoffとのprovenance接続を再検証する。
5. evidenceとmaster specを更新しcommit/pushする。
