# Connector Eventbrite checkout-frame trigger plan (Item 19E-D1)

## Goal

Eventbriteのstrict eligible candidateだけについて、canonical detail pageの一意な公式CTAを開き、同じevent IDへ結合された公式checkout iframeの出現までをBrowser Harnessで安全に観測する。ticket数量、Register、attendee form、最終登録はこのsliceで操作しない。

## Ponytail gate

- 新agent、API client、DB、queue、scheduler、browser sessionを追加しない。
- 既存`connector-production-browser-harness.js`のprovider-specific trigger seamとmatching testだけをcopy-tweakする。
- 変更はproduction 1 file 約60–90 LOC、test 1 file 約90–130 LOCをsoft targetとする。
- Eventbrite全checkoutを実装せず、実測済みの最初の境界だけを閉じる。

## Owned files

1. `apps/mr-bot/lib/connector-production-browser-harness.js`
2. `apps/mr-bot/lib/connector-production-browser-harness.test.js`

## RED

追加testは最低限、次を先に失敗させる。

1. exact candidate binding: `eventbrite-event://event/<id>`と`https://www.eventbrite.com/e/<slug>-tickets-<id>`が一致し、current page URLもcanonical exactのときだけ許可する。
2. top CTA: visible/enabledな`[data-testid="conversion-bar-checkout-button"]`がexact 1、tag button、type button、labelが`Get tickets`または`Reserve a spot`のときだけpublic controlを返す。fuzzy/hidden/disabled/duplicate/wrong event/wrong current URLはcontrols 0。
3. action: 上記controlはEventbrite専用triggerとして`submit/ax_click`だけを許可する。generic button、別provider、別token、duplicate semantic controlはoperate 0。
4. post-click: action成功は`page.frames()`内にorigin `https://www.eventbrite.com`、pathname `/checkout-external`、query key `eid`がcandidate event ID exact、frame exact 1が期限内に現れた場合だけ。0/duplicate/wrong origin/path/eidはfailed。
5. safety: ticket stepper、iframe Register、attendee input、final submit、provider readback、Calendar/evidence/Telegramは0。既存provider testは不変。

## GREEN

- `eventbrite`をHarness provider allowlistへ追加するが、workflow injection/readback/native provider orderは変更しない。
- Eventbrite candidate binding、semantic trigger判定、bounded checkout-frame waitだけを追加する。
- inspectorはmain pageのexact top CTAだけをpublic control化する。iframe内容はこのsliceではcontrol化しない。
- actorは既存`operatePageControl`を再利用し、クリック後のexact frameをparent側で確認する。
- checkout frame確認不能は`{ status: "failed" }`でfail closedする。登録成功、pending、applied_bundleを返さない。

## Verify

- focused Harness test
- stable production/operations/provider combined test
- `node --check`
- exact 2-file diff、secret/private value 0
- schedule labels unloaded、Connector process 0、CDP target-ledger/current-page intersection 0

## Deferred next slice

Eventbrite checkout frame内のticket rowを実DOMで再計測し、無料ticket exact 1選択、Registerによるattendee form遷移、required answers、最終Register＋parent readbackを別TDD sliceで閉じる。
