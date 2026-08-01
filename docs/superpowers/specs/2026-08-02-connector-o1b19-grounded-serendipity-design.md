# Connector O1B-19 grounded goal / serendipity評価設計

status: APPROVED
owner: Connector
date: 2026-08-02 JST

## 実provider調査

2026-08-02 JSTに既存CloakBrowser daily-driverでLuma Tokyoをread-only実測した。終端6round、32候補。
一候補の公式JSON-LDにはdescription 913文字、organizer 2件、開始・終了、会場名、住所、緯度経度が
存在した。`attendee`と`performer`は0件だった。rendered pageのpublic profile link 2件はorganizer数と
一致し、参加者とは証明できない。

したがって参加者情報が非公開のeventで、参加者像や所属を推測してはならない。providerが明示した
attendee情報だけを読み、無ければ`unavailable`として評価へ渡す。

## 目的

O1B-18の全候補保持rankingを入力に、event本文、主催者、参加者、場所、時間を読み、Daisの
自然言語goalとの整合とserendipity potentialを根拠付きで評価する。

## source契約

deterministic provider parserが次を取得・正規化する。

- `description`: 公式JSON-LD本文
- `organizers`: 公式JSON-LDの公開name
- `participants`: 公式JSON-LD attendeeの公開descriptor。無ければ空配列
- `participant_visibility`: `public_metadata / unavailable`
- `venue_name / venue_address`
- `starts_at / ends_at`

HTMLやmodelが、欠けた参加者・住所・時間を補完しない。O1B-17 snapshotとO1B-18 rankingの
in-process provenanceを両方要求する。

## agent判断

Geminiは同日の全候補について次を返す。

- `goal_alignment`: `strong / moderate / weak / unknown`
- `serendipity_potential`: `high / medium / low / unknown`
- 人間向けのgoal理由とserendipity理由
- `description / organizers / participants / place / time`の5 factor assessment
- 各factorの`used / unavailable`と、usedならsourceに完全一致するevidence excerpt

全候補をexactly onceで返し、array順をO1B-19のgrounded rankingとする。参加者非公開はevent除外理由に
せず、factorだけ`unavailable`にする。model failure、欠落、重複、未知ref、sourceにないexcerptは
fail closedし、keyword/regex fallbackを作らない。

## 完了条件

1. 実provider fieldをverified detailと日付snapshotへ伝播する。
2. 5 factorをexactly onceで検証し、欠けた参加者をinventしない。
3. O1B-18 rankingの全event refをexactly once保持する。
4. 実Gemini evalでgrounding、全候補保持、期待上位、missing participant honestyを確認する。
5. 実Luma readback、outbound全回帰、証拠、spec、commit、pushが揃う。

