# Connector Eventbrite marketing opt-out plan (Item 19E-D4c2)

## Goal

Eventbrite attendee exact4 fieldsの入力後、既定ONになり得る既知marketing checkboxをsame-event checkout frameで安全にOFFへ変更する。最終`Register`のclick、provider effect、readback、evidenceはこのsliceでは0件。

## Ponytail gate / size

- 既存attendee inspector、event-bound control、same-frame operationを拡張し、新規service/workflow/selector fallbackは作らない。
- Harness production/test 2 filesと、production `runFallback`が専用methodを許可するadapter 1 fileのexact 3 files。soft target production 55–90 LOC、test 80–125 LOC。
- DOM property代入、`force` click、coordinate click、未知checkbox操作は作らない。

## Exact observation contract

1. parent canonical、official child exact1/eid、required attendee fields exact4 completedの既存contractを維持する。
2. marketing inputはcase-sensitive exact name `organizationMarketingOptIn`または`ebMarketingOptIn`だけを対象にする。各name raw countは0または1。duplicate、wrong tag/type、required、hidden/detached/disabledはfail closed。
3. checked inputはnon-empty unique `id`と、same frame内のexact `label[for=<id>]` raw/visible count1を要求する。対応labelへだけ`eventbrite_marketing_opt_out_<organization|eventbrite>_<eventId>`をbindする。
4. checked対象だけをkind checkbox、required true、completed false、submittable falseとして公開する。unchecked対象は操作controlを公開しない。
5. checked対象が1件以上ならfinal Register controlは公開しない。全対象がuncheckedかつ既存primary contractが成立したときだけfinal Registerをread-only公開する。

## Exact action contract

1. marketing tokenだけを`purpose=fill / method=ax_uncheck`へ写像する。generic checkboxの`ax_check`は不変。
2. private value resolverは呼ばない。same parent canonical、same official child exact1/eid、same Frame、selected input/label exact1、checked=trueを操作直前に再検査する。
3. `operatePageControl`はtokenをbindした可視labelへ通常の`click()`をexact1回だけ行う。`force`、coordinate、DOM property assignmentは0。
4. 操作後にsame frameを再観測し、selected marketing tokenが消え、対応inputがuncheckedになった場合だけsuccess。page/frame/eid/DOM drift、locator0/2、click error、postcondition falseはfailed。
5. `eventbrite_attendee_register_*`は引き続きunbind/unactionableで、final click/final-effect wait/readbackは0。

## Fresh-review scope correction

1. click直前にtokenをmarketing labelからprimary Registerへ移す反例で、postcondition failedでもfinal click 1が発生した。`ax_uncheck` operation境界はtoken count1だけでなく、exact label tag/for、known input name/id/type/optional/visible/enabled/checked、raw identity exact1を再拘束してからclickする。
2. marketing input idの一意性はinput集合だけでなくinspection対象全elementsでraw exact1を要求する。同じidのbutton/inputはcontrol 0。
3. dedicated `ax_uncheck`はBrowser Harness adapterのfill allowlistとHarness mutation dedupeへ追加する。Eventbrite providerはまだHarness workflow mapへ未統合なので、adapter単体E2Eを既存Harness test内に置き、proposalした`fill/ax_uncheck`がperformへexact1回届くことを確認する。Eventbrite full `runFallback`、workflow injection/dedupe E2Eはfactory/native統合sliceへdeferする。adapter test file、新抽象化、別methodへの意味的偽装は追加しない。

## TDD / verification

1. RED: checked organizer marketing input＋可視exact labelからopt-out controlを期待し、現行fields onlyを確認する。
2. checked2件のone-at-a-time、unchecked no-control＋final-visible、duplicate/wrong/hidden/disabled/required input、missing/duplicate/hidden/wrong-for labelをtable regressionにする。
3. action RED: exact label click1、resolver0、post uncheckedを期待する。wrong action、page/frame/eid/DOM drift、locator0/2、click error、postcondition false、final token action0を回帰化する。
4. GREEN後、focused Harness、adapter単体E2E、Eventbrite/minimal-production/native adjacent、syntax、`git diff --check`、3-file ownership、4 labels unloadedを確認する。
5. fresh Sol reviewでCritical/Important 0を得てからstableへ統合する。

## Deferred

final Register click-once、registered/pending readback、ticket-step effect-unknown reconciliation、factory/runFallback/native provider order、実`applied_bundle`、evidence/Telegram、schedule load。
