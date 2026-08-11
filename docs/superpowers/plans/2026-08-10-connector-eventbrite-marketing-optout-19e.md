# Connector Eventbrite marketing opt-out plan (Item 19E-D4c2)

## Goal

Eventbrite attendee exact4 fieldsの入力後、既定ONになり得る既知marketing checkboxをsame-event checkout frameで安全にOFFへ変更する。最終`Register`のclick、provider effect、readback、evidenceはこのsliceでは0件。

## Ponytail gate / size

- 既存attendee inspector、event-bound control、same-frame operationを拡張し、新規service/workflow/selector fallbackは作らない。
- Harness production/test 2 filesと、production `runFallback`が専用methodを許可するadapter 1 fileのexact 3 files。soft target production 55–90 LOC、test 80–125 LOC。
- DOM property代入、coordinate click、未知checkbox操作は作らない。実inputはiframe viewport外でPlaywright標準`uncheck()`がtimeoutし、page-owned DOM `click()`はmethod overrideを受けるため、exact INPUT＋known name＋event tokenへPlaywright `uncheck({ force: true })`だけを許可する。`force`はviewport actionabilityだけを迂回し、state-aware action対象のidentity条件は緩めない。

## Exact observation contract

1. parent canonical、official child exact1/eid、required attendee fields exact4 completedの既存contractを維持する。
2. marketing inputはcase-sensitive exact name `organizationMarketingOptIn`または`ebMarketingOptIn`だけを対象にする。各name raw countは0または1。duplicate、wrong tag/type、required、hidden/detached/disabledはfail closed。
3. live official checkoutではknown input 2件に対応する`label[for=<id>]`が0件で、label依存は実DOMと不一致だった。checked inputはnon-empty `id`、inspection対象全elementsでid raw exact1、known name/type/optional/visible/enabled/checkedを要求し、input自身へ`eventbrite_marketing_opt_out_<organization|eventbrite>_<eventId>`をbindする。control labelはprivate値を含まない固定`Organizer marketing opt-out` / `Eventbrite marketing opt-out`を使う。
4. checked対象だけをkind checkbox、required true、completed false、submittable falseとして公開する。unchecked対象は操作controlを公開しない。
5. checked対象が1件以上ならfinal Register controlは公開しない。全対象がuncheckedかつ既存primary contractが成立したときだけfinal Registerをread-only公開する。

## Exact action contract

1. marketing tokenだけを`purpose=fill / method=ax_uncheck`へ写像する。generic checkboxの`ax_check`は不変。marketing identity/actionはlabel DOMへ依存しない。
2. private value resolverは呼ばない。same parent canonical、same official child exact1/eid、same Frame、selected input/label exact1、checked=trueを操作直前に再検査する。
3. observerは可視label/forを含むidentity確認後、operation tokenをknown input自身へbindする。`operatePageControl`は`input[data-lm-connector-control=token][name=knownName]` exact1からstable `ElementHandle`とoriginal idを一度だけ取得し、そのsame handleのtag/name/id/type/optional/visible/enabled/checked/connectedを確認後、handleへPlaywright `uncheck({ force: true })`をexact1回だけ行う。lazy locator再解決、page-owned getter/method、label click、coordinate、DOM property assignmentは0。
4. 操作後にsame canonical/frame/eidとsame original handle/idで、tag/name/id/type/optional/visible/enabled/connected/uncheckedを500ms連続して確認した場合だけsuccess。marketing invalid/hiddenをabsentと同一視しない。page/frame/eid/element identity drift、locator0/2、action error、async controlled reversion、postcondition falseはfailed。
5. `eventbrite_attendee_register_*`は引き続きunbind/unactionableで、final click/final-effect wait/readbackは0。

## Fresh-review scope correction

1. click直前にtokenをmarketing labelからprimary Registerへ移す反例で、postcondition failedでもfinal click 1が発生した。`ax_uncheck` operation境界はtoken count1だけでなく、exact label tag/for、known input name/id/type/optional/visible/enabled/checked、raw identity exact1を再拘束してからclickする。
2. marketing input idの一意性はinput集合だけでなくinspection対象全elementsでraw exact1を要求する。同じidのbutton/inputはcontrol 0。
3. dedicated `ax_uncheck`はBrowser Harness adapterのfill allowlistとHarness mutation dedupeへ追加する。Eventbrite providerはまだHarness workflow mapへ未統合なので、adapter単体E2Eを既存Harness test内に置き、proposalした`fill/ax_uncheck`がperformへexact1回届くことを確認する。Eventbrite full `runFallback`、workflow injection/dedupe E2Eはfactory/native統合sliceへdeferする。adapter test file、新抽象化、別methodへの意味的偽装は追加しない。
4. page-contextの`input.click` getter/methodはoverride可能なので操作primitiveにしない。exact input locatorのPlaywright state-aware uncheckを使い、別label/button/final controlはselector上操作不能にする。同期OFF後に次taskでONへ戻るcontrolled inputは500ms stability gateでfailedにする。
5. Playwright locatorはcount後もlazyに再解決されるため、countとactionの間でhidden decoyへtoken/nameを移せる。operationはcount時のsame `ElementHandle`を保持し、post stabilityもそのoriginal handle/idを追跡する。decoy swapはdecoy/final作用0、status failed。

## TDD / verification

1. RED: checked organizer marketing input＋可視exact labelからopt-out controlを期待し、現行fields onlyを確認する。
2. checked2件のone-at-a-time、unchecked no-control＋final-visible、duplicate/wrong/hidden/disabled/required input、missing/duplicate/hidden/wrong-for labelをtable regressionにする。
3. action RED: exact label click1、resolver0、post uncheckedを期待する。wrong action、page/frame/eid/DOM drift、locator0/2、click error、postcondition false、final token action0を回帰化する。
4. GREEN後、focused Harness、adapter単体E2E、Eventbrite/minimal-production/native adjacent、syntax、`git diff --check`、3-file ownership、4 labels unloadedを確認する。
5. fresh Sol reviewでCritical/Important 0を得てからstableへ統合する。

## Trust boundary / live acceptance

- Exact official `https://www.eventbrite.com/checkout-external?eid=<same-event>` first-party UI semanticsを信頼する。DOM ambiguity、identity drift、lazy-locator race、hidden/disabled/duplicate control、async controlled reversionは防御対象。公式Eventbrite自身がmarketing checkboxのevent handlerから意図的にregistration fetch/submitを起こす悪意は脅威モデル外。これはtop CTA/ticket actionも同じfirst-party codeを信頼する既存境界であり、browser parentから任意first-party JavaScript effectを完全遮断しない。
- コードreview後、実official checkoutでknown checked inputをexact1回OFFにし、500ms安定、final `Register` read-only exact1、registered/completion readback 0、final click 0、Calendar/evidence/Telegram effect 0を確認する。live観測contractはmarketing 2、checked 1、visible/enabled 2、required 0、label-for 0、primary exact/visible/enabled/Register 1。このlive proofがない限りD4c2を完了扱いにしない。

## Deferred

final Register click-once、registered/pending readback、ticket-step effect-unknown reconciliation、factory/runFallback/native provider order、実`applied_bundle`、evidence/Telegram、schedule load。
