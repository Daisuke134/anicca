# O1B-17 Luma日別完全inventory 実装計画

**Goal:** Luma Tokyo/In Person main timelineをvirtualization末尾まで読み、今日〜20日後の各日についてcompleteな候補一覧を作る。

## Contract

- exact `https://luma.com/tokyo?k=p`をshared daily-driverで読む。
- 消えるcardを累積し、page endはstable height + atEnd + no-newを複数roundで証明する。
- DOMの日付見出しをcardごとに取得し、今日/明日/M月D日をTokyo ISO dateへ決定的に変換する。
- 日付未解決eventが一件でもあればday inventoryをcompleteにしない。
- rolling coverage 21日の全日をcandidate 0の日も含めて出力し、global end proofへ束縛する。

## Steps

1. 今日label欠落と日別partition欠落をRED testで固定する。
2. snapshot/normalizer/collectorへexplicit nowとISO event dateを追加する。
3. 21日daily inventory builderを追加し、全日completeをglobal end proofへ束縛する。
4. shared :9222でlive exhaustive readbackし、全回帰、evidence、spec、commit/pushを完了する。
