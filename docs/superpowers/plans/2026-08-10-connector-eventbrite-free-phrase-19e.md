# Connector Eventbrite free-phrase eligibility repair (Item 19E-D2)

## Goal

Eventbrite detail本文の明示的な無料表現を費用markerと誤認せず、一方で無料入場に付随するminimum purchaseを確実にpaidとして除外する。

## Ponytail gate

- 新parser/service/agentを作らず、既存Eventbrite workflowのbody eligibility predicateだけを修正する。
- production 1 file 約15–30 LOC、test 1 file 約35–60 LOC。
- ticket/frame/Harness/factory/native order/readbackは変更しない。

## Owned files

1. `apps/mr-bot/lib/connector-eventbrite-workflow.js`
2. `apps/mr-bot/lib/connector-eventbrite-workflow.test.js`

## RED

1. `参加費無料`、`入場無料`、`free admission`、`no participation fee`を含み、zero offer/identity/Tokyo/controlが有効なdetailはeligibleとなる。
2. 上記無料表現と同じ本文に`one drink minimum`、`minimum purchase`、`purchase required`、`ワンドリンク必須`のいずれかがあればeligible 0。
3. `参加費 1,000円`、`admission fee ¥1,500`、`paid at door`等の既存paid markerはeligible 0を維持する。
4. explicit free phraseを除去した残本文だけへpaid markerを適用し、free substringで本文全体をwhitelistしない。

## GREEN

- body textを正規化し、exact explicit-free phrasesだけを空白へ置換する。
- 残本文へ既存money markerと新minimum-purchase markerを適用する。
- Offer price zero、CTA、identity、Tokyo、Calendar順序は不変。

## Verify

- focused Eventbrite workflow test
- Harness/minimal production/operations adjacent test
- syntax、diff check、exact 2 files
- 実Eventbrite free detailをproduction workflowで再測定し、eligible countが1へ修復されること。Calendar conflictならcandidate 0を正しく維持する。
