# Connector O1B-24 event spend policy 設計

## 実測

- 実Luma Tokyo inventory 20件をread-only監査。
- JSON-LD `offers`は20/20に存在し、`price`、`priceCurrency`、`availability`を持つ。
- 無料14件、有料6件。currencyはUSD 14件、JPY 6件。
- 自動支出上限と保存済み決済手段のverified evidenceは現在0。したがって現在のpaid capは0。

## 原則

1. Calendar/移動gateを通った候補の中で、無料候補を有料候補より先にする。
2. preference/goal/serendipityは各価格group内の順序に使い、無料優先を破らない。
3. price/currencyが不明な候補を無料扱いしない。
4. 有料候補はimmutable policyのper-event cap、rolling 30日cap、remaining amountを全て満たす時だけ許可する。
5. verified saved payment method refがなければ有料checkoutを開始しない。
6. policy内なら都度承認を要求せず実行する。policy外なら無料/別候補へ進み、loop全体を止めない。
7. card番号、CVV、有効期限、holder名をcode・DB・log・Telegramへ保存しない。
8. paid submit後の不明状態は二重決済せずreconciliationへ送る。

## 現在のpolicy

```text
paid_enabled: false
per_event_cap: 0
rolling_30_day_cap: 0
saved_payment_method_ref: none
```

これは都度承認を導入する意味ではない。支出権限が未設定の間は無料候補だけでcoverageを進める。

## 完了条件

offer正規化、無料優先、currency別minor unit、policy provenance、saved payment evidence、policy内checkout、
policy外次候補、unknown payment reconciliationをtestし、実inventoryのprice分類を証拠化する。
