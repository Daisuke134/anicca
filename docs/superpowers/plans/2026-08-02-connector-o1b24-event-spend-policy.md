# Connector O1B-24 実装plan

1. Luma JSON-LD offersをoriginal currency/minor amountへ正規化する。
2. verified event spend policyを実装する。
3. calendar-eligible候補をfree-firstで並べ、paid候補をpolicy gateする。
4. saved payment method evidenceとpaid checkout effect fenceを追加する。
5. events packへ接続し、実inventory read-only分類と全回帰を行う。
6. evidence/master specを更新しO1B-25へ進めcommit/pushする。
