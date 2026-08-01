# Connector O1B-17 Luma日付別inventory設計

status: APPROVED
owner: Connector
date: 2026-08-02 JST

## 目的

Luma Tokyoの表示上位だけで探索を終えず、仮想scrollの終端まで得た全candidateを、信頼できる
event detailのISO開始時刻でrolling 21日へ投影する。

## 採用設計

1. 既存`collectLumaInventory`が、終端・新規0件・scroll height安定を連続3回確認する。
2. 終端証明済みinventoryの全canonical URLを、同じCloakBrowser daily-driverで一件ずつ読む。
3. 公式JSON-LDから開始・終了、attendance mode、開催status、会場を正規化する。
4. discoveryの日本語`date_label`ではなく、ISO開始時刻をIANA timezoneでlocal dateへ変換する。
5. 21日すべてを一度ずつ出力し、scheduled + in_personだけを該当日へ格納する。
6. discovery終端、candidateとdetailの完全一致、重複なしが揃わなければsnapshotを作らない。

## 完全性契約

日付別inventoryの`complete`は、次の論理積である。

```text
global Tokyo page end proven
AND every discovered canonical URL inspected
AND every detail normalized from provider JSON-LD
AND exact URL-set equality and no duplicates
AND exact projection to the same verified rolling 21-day snapshot
```

日付の候補0件は「その日まで読み切った」ことを示すだけであり、`unavailable`でも
`covered_existing`でもない。O1B-20以降の別source探索とO1B-23のCalendar照合が終わるまで`open`を維持する。

## 境界

- O1B-17ではcategory ranking、serendipity評価、RSVP、Calendar書込をしない。
- browser、cookie、認証情報、guest keyをsnapshotへ保存しない。
- 意味判断をkeyword/regexで代替しない。ここではprovider metadataのparseと日付投影だけを行う。
- 一件でもdetail取得不能なら部分snapshotを成功扱いせずfail closedする。

## 出力

content hashを持つimmutable snapshotとして、coverage snapshot ID、取得時刻、timezone、
candidate/detail/excluded件数、21日それぞれのevent refとcanonical URLを保持する。

