# Connector O1B-23 実装plan

1. 既存gog transportへ全calendar/全page read-only snapshotを追加する。
2. timed/all-day/free/cancelledを正規化するverified busy inventoryを実装する。
3. route所要時間込みcandidate interval gateをtest先行で実装する。
4. 同日候補loopのattempt直前へgateを接続する。
5. verified registration後だけidempotent Calendar writeを接続する。
6. 実5 calendar/21日read-only検証、focused/full regression、evidenceを作る。
7. master specをO1B-24へ進めcommit/pushする。
