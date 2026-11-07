# Anicca iOS Product Growth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task. チェック欄は実行手順の参照であり、順序・完了状態は統合SSOTだけに記録する。

**Goal:** Anicca iOSの画面別計測をMixpanel一本で本番運用し、既存Openで確認できるようにして、同一候補buildの全画面Maestro動画を提示した後にだけ審査へ提出する。

**Architecture:** iOSは既存SwiftUI/UIKit・StoreKit/RevenueCat・Mixpanelを使い、PostHogの重複経路を除く。Aniccaの集計はLife Manager既存product summaryから既存Open snapshotへつなぎ、dashboard ownerの`anicca-products` repoで表示する。第二の分析基盤/dashboard/runtimeを作らない。

**Tech Stack:** SwiftUI、UIKit、Swift focused tests、Maestro、APNs、RevenueCat、Mixpanel、既存Life Manager collectors、anicca-products Open snapshot、ASC CLI、Xcode Cloud（署名buildのみ）。Xcode UIは使わない。

**Spec:** `docs/superpowers/specs/2026-11-06-anicca-ios-product-growth-design.md`

**パスの基準:** `apps/`・`docs/`・`config/`・`skills/`で始まるpathはrepo基準。それ以外のiOS関連path（`aniccaios/`・`aniccaiosTests/`・`maestro/`・`fastlane/`・`scripts/`・`README.md`）は `apps/mobile/anicca-ios/` 基準。コマンドの実行cwdはrepo rootとする。

## Global Constraints

- 現在順はG2完了→G4 build 820由来Mixpanel実受信→G4.1 Open実集計/鮮度/表示→G5同一build E2E動画と既存審査状態の整合。G1/G3は検証済みとして再利用する。
- 1.9.8/build 820は既にApp Reviewで`WAITING_FOR_REVIEW`。この確認では取り消し・追加提出をしない。G4/G4.1と同一build E2Eの未完了を完了扱いせず、既存submissionを重複作成しない。実装順/状態の唯一の正本は統合SSOT `ANICCA-PRODUCT-GROWTH`。
- G6/G7全アプリ展開とG8〜G10自動改善はその後へ保持する。G4.1はAniccaだけの提出前必須slice。
- source=`Daisuke134/life-manager`、app=`apps/mobile/anicca-ios`、既存private configとowner/leaseを使用。
- 最小回帰のRED→GREEN、正本mainから署名build、公式readback。アプリのPackage.swiftはmacOS card生成用でありiOS検証の代替にしない。
- UI mockのデモ値を本番へ固定しない。初回soft paywall、現行購入権限/各対応言語の動作を維持。
- ダッシュボード/公開exportの別owner、配信owner、共有profile、他者のstateへ独断で同時変更しない。
- 容量不足は所有者を確認した再生成可能な不要物を整理して解消し、保存/pushを完遂する。
- App Store Connectの提出/取消/状態確認はASC CLIで行う。署名済みartifactの作成は既存Xcode Cloud、Maestro実行/録画はMac MiniのSimulatorを使い、Xcode UIは開かない。
- 現在の限定公開YouTube動画3本はSimulator build 819で、署名candidateとのsource/build一致は未証明。全screenを含み同一の署名candidateへ結び付いた録画は別途必要。
- ASC read-only readback（2026-11-08 03:05 JST）は1.9.8/build 820=`VALID`、review submission `46f41ee2-5e57-4b09-8dd6-98a890b7a0f7`=`WAITING_FOR_REVIEW`。前submission `9fa35898-1eee-44ce-942b-630780d9133b`は`COMPLETE`。現在の審査対象が存在するため、新しいsubmissionは作らない。状態の正本は統合SSOT。

## Review Focus

1. 対話swipe中のSwiftUI更新/通知遷移で古いindexに戻らない。Task2の連続swipe回帰で確認。
2. cold-start中/本文のみ/未知IDの通知でも同じ文言を保持。Task2のnavigation回帰で確認。
3. 既存有料・途中onboarding・通知拒否・storefront変更で権限/進行を失わない。Task1/3の回帰で確認。
4. likeがpagerを途中で並べ替えず、catalog外通知の保存が消えない。Task2の保存回帰で確認。
5. sparse/late report、未成熟cohort、重複購入/restoreを0や売上に変えない。Task3/5のfixtureで確認。

## Task 1: 初回体験・見た目・購入画面（G1）

**Files:** `apps/mobile/anicca-ios/aniccaios/Onboarding/{OnboardingFlowView,OnboardingStep,OnboardingBibleViews,PaywallVariantBView,PaywallPackageSelection}.swift`、`AppState.swift`、`Views/Feed/{FeedRootView,QuoteCardView,ThemeStore,SettingsSheet}.swift`、`Resources/*.lproj/Localizable.strings`、`aniccaiosTests/OnboardingV2Tests.swift`、`scripts/tests/PaywallPackageSelectionTests.swift`。

**Consumes:** 現行profile/onboarding保存値、RevenueCat CustomerInfo/Offering、StoreKit localized prices。**Produces:** 目的→最初の文言→任意reminder→soft paywall→feed、安定accessibility ID、後続event用のflow/screen ID。

実caller確認による補足: native画面は `aniccaios/Onboarding/InitialAffirmationExperience.swift` に置く。旧 `OnboardingV2Tests.swift` は現在targetに登録されず廃止enumを参照するため、経路回帰は `scripts/tests/OnboardingJourneyTests.swift` でproduction `OnboardingStep.swift` を直接compile/runし、画面/復帰はXcodeとMaestroで検証する。

- [ ] 既存保存値とpaywall callerを読む。既存完了/有料、途中step、通知拒否、offering失敗、国変更の期待動作をspecへ照合する。
- [ ] 対応する既存XCTest/Swiftテストへ、通知拒否でも進む・有料へ再質問しない・国不一致商品を買えないケースを追加し、修正前の失敗を記録する。
- [ ] 不要な質問/処理演出を外し、native画面をmockの構造へ合わせる。Pro特典は現行の実権限から文言を確定する。
- [ ] Xcodeの対象scheme/実在するtest targetとavailable destinationを取得し、追加したfocused testを `xcodebuild test -project apps/mobile/anicca-ios/aniccaios.xcodeproj -scheme aniccaios -destination 'platform=iOS Simulator,id=<owned-UDID>' -only-testing:<resolved-target>/<test-class>` で実行する。Expected: 実在classの対象testが全PASS、未実行を成功にしない。
- [ ] localization parityと購入wiringの既存検証を実行し、diff確認→fetch→commit/push。新規dependencyや不要な互換層を入れない。

## Task 2: swipe・通知・catalog・保存/個人化（G2/G3）

**Files:** `aniccaios/Views/Feed/{VerticalPager,FeedRootView,QuoteCardView,SettingsSheet}.swift`、`Services/{QuoteNavigationCoordinator,QuoteProvider,LikedQuotesStore,PushTokenService}.swift`、`AppDelegate.swift`、`Notifications/NotificationScheduler.swift`、`aniccaiosTests/{QuoteNavigationCoordinatorTests,PushTokenServiceTests}.swift`。必要な小さい推薦/保存testは同targetへ追加する。

**Consumes:** `Quote(id:text:)`、`QuoteNavigationRequest(quoteID:alertBody:)`、目的/like/既存設定。**Produces:** 安定ページ遷移、通知と同じ文言、実設定の表示、タグ付き600件以上の英語catalogと好みに応じた次候補。

- [ ] actual releaseとpayload、pager delegate/update、notification pendingとbackend配信owner/callerを比較する。既存同文言修正の不足を一つずつ再現する。
- [ ] 本文のみ・未知ID・catalog未準備・cold/warm・重複tapに加え、大文字小文字が異なるcatalog一致と本文追加時も受信 `alertBody` を表示する回帰を先に失敗させる。同じIDが現在のpersonalized feedにある場合も、既存要素を解決済み本文で置換してから遷移する。gesture中like/通知遷移、catalog外文言保存も回帰対象にする。
- [ ] 遷移中のindex同期と保留要求の消費を最小修正。固定4件を実設定へ接続し、remote/localは実配信receiptに基づいて一ownerにする。backend変更は所在と所有が確定した対象だけへ行う。
- [ ] EN catalogを600件/12カテゴリ以上へ増やし、ID重複・本文重複・空文・カテゴリ件数のfixtureを追加する。好み/likeの候補重み、直近20件の抑制、枯渇時fallbackと解除/再起動保持を確認する。候補は対話遷移中に入れ替えない。
- [ ] 通知navigationのproduction sourceを `swiftc` で直接compileする `scripts/tests/QuoteNavigationTests.swift` と既存の通知/保存focused testsを実行。Expected: 新規回帰と既存通知/保存testがPASS。Maestro連続swipeはTask5で同じcandidate SHAを使用する。署名buildは既存Xcode Cloud経路で行う。
- [ ] source acceptance→fetch→commit/push。実機APNsが未確認なら未確認と記録し、injection成功で代替しない。

## Task 3: 行動・課金計測の正確化（G4）

**Files:** `apps/mobile/anicca-ios/aniccaios/Services/{AnalyticsManager,SubscriptionManager}.swift`、`AppDelegate.swift`、`Config.swift`、Task1/2 screen/action caller、`PurchaseObservationLedger.swift`、`PlanSelectionStepView.swift`、`RetentionOfferSheet.swift`、`aniccaios.xcodeproj/project.pbxproj`とworkspace `Package.resolved`、関連focused tests。project token/credentialsはprivate configで保持し、diff/logへ出さない。

**Consumes:** Mixpanel SDK event history、stable anonymous/customer ID、screen/quote/notification ID、StoreKit transaction/RevenueCat entitlement。**Produces:** Mixpanel一本のevent契約、画面別離脱funnel、restoreを含む課金観測、service receipt。PostHogは送信先から除く。

- [x] 18個のAnalyticsScreenIDをproduction callerへ対応付け、event/caller、paywall/restore、identify/reset、PostHog経路を記録。現行linear onboardingに戻る操作はなく、`onboarding_step_back`は未使用enumのみと確認。source mappingの完了はservice受信・実coverageの証明とは分離する。
- [x] Mixpanel Swift SDKをstable 7.1.0（revision `38e63de7d71a2b6787bbd190ef8fcc04d053f259`）へpinし、PostHog Package/Info.plist config/SDK captureを除去する。focused provider-contract testでPostHog経路なしを確認。
- [ ] Mixpanel accountのExperiments entitlement・MEU allowance・project regionを公式readbackし、使える機能だけを有効化する。
- [x] 独立レビュー指摘: background→activeで同じ画面のvisitを再開し、その後の明示的な次画面遷移を記録する。サインアウトではactive/suspended visitを消去し、session IDを更新する。純Swift lifecycle regressionをRED→GREENで確認する。
- [x] shared modifierとOnboardingの再表示をscreen/flow単位のdedupe経路へ統一し、foreground復帰時の同一画面再entryがexitを作らないことをcontract testで確認する。
- [x] CLI focused fixturesで同一screen instance重複、前後移動のnext screen/滞在時間、background時にexitを送らないことを確認。`PurchaseObservationTests`はnil/blank/duplicate/replayed transactionを確認し、wiring testsはtrial/restore callerとflowを照合。event contract testは表示価格/収益額/transaction IDをclient payloadへ入れない。
- [ ] StoreKit/RevenueCat sandboxでrestore/trial/error、missing/different currency、offline resendを隔離し、Mixpanel service receiptと重複0をreadbackする。local SDK queue evidenceだけでservice受信を完了扱いしない。
- [x] 固有transactionの観測結果をactive/retention/legacyの共通入口にし、同じtransactionの重複をオンボーディング成功からも除く。`settings_subscription`は汎用結果だけにし、purchase/trial/restore全eventへ`flow_id`を付ける。focused purchase/wiring testsで確認。実収益sourceはRevenueCat/Appleと区別する。
- [ ] screen/flow/activation/notification/paywall/product/purchase/trial/restore/exposureにevent/property contractを付け、raw affirmation text/PII/secretを送らず内部buildを識別する。画面終了は明示的遷移だけを送り、OS killは次step観測窓によるdrop-off推定とラベルする。
- [ ] focused tests後にMixpanel側で同じtest identityのevent・properties・build/locale/variant・時刻をreadbackし、同一event/transaction重複0を照合する。local log/SDK configだけでは完了にしない。
- [ ] source acceptance→fetch→commit/push。provider receiptと根拠をSSOTへ残す。

## Task 4: Aniccaの画面別funnelを既存Openへ接続（G4.1）

**iOS source:** `apps/mobile/anicca-ios/aniccaios/Services/AnalyticsManager.swift`と各screen caller（Task3）。**集計source:** `Daisuke134/anicca-products`のOpen owner `apps/landing/scripts/open-mixpanel-analytics.mjs`、`apps/landing/public/open/index.html`、既存`data.json`、`.github/workflows/netlify-deploy.yml`。Life Managerの`marketing-product-summary.js`はproduct-pack readerでMixpanel collectorではなく、このsliceでは経由しない。ASC collector`open-app-store-analytics.mjs`はstore acquisitionのみ。

**Consumes:** Mixpanel aggregate、App Store Connect/RevenueCatの公式cohort/収益、app/date/locale/campaign/release/experiment dimensions。**Produces:** 公開個人データを含まないAnicca screen funnel panelと日次snapshot。

**最新実装readback（2026-11-08 02:52 JST）:** PR [#904](https://github.com/Daisuke134/anicca-products/pull/904)と[#905](https://github.com/Daisuke134/anicca-products/pull/905)はmain統合済み。最新Landing run [`42397787829`](https://github.com/Daisuke134/anicca-products/actions/runs/42397787829)はSUCCESSし、Mixpanel Raw Event Export API queryは`no_events, 0 screens, 2026-10-30–2026-11-05`を返した。公開`/open/data.json`もview/exit 0、screens/breakdowns空を返す。これは最新の成功queryで、以前の`missing_service_account`ではない。ただしwindowはbuild 820の2026-11-07 upload前なので、build 820の実event到達を証明しない。JSON `updated_at=02:37 JST`と`observed_at=02:52 JST`の差も残る。

- [x] 過去の個別`mixpanel-headless` CLI/OAuth preflightはこの実行環境ではAccount/Project noneで未完了。ただし、最新Open production run `42397787829`のExport API queryは成功し、既存のcollector認証経路でproject `3970220`のquery結果を取得した。Open収集のためのGoogle OAuthやservice account新設は現在のblockerではない。
- [ ] build 820由来のscreen eventを利用可能な配布/検証経路で発生・readbackし、project/region、`app_id`, `app_environment`, `app_build`, event/property, timestamp, identity、重複0を照合する。simulator/sandbox trafficをproduction eventと混ぜない。
- [x] 既存hourly Netlify workflowへcollectorを1 step追加し、`screen_viewed`/`screen_exited`を`app_id`, app environment, date windowで絞り、`screen_instance_id`単位で重複排除するコードをPRに実装。
- [x] `product_analytics.anicca_ios`のstatus, observed_at, source, data window, maturity, coverage, numerator/denominator, app/build/locale/country, nullable ratesを実装。raw user ID、個人event、affirmation本文を出力しない。
- [x] `check-open-data`/collector testsでmissing/invalid analytics、denominator、successful empty export、aggregation/filter/privacyを検証。PR内の関連39 testsはPASS。
- [x] `index.html`へscreen view数、next-screen観測、成熟24時間後の未観測数/率、分母/期間/buildを表示するtableを実装し、未観測をchurn確定と呼ばない。
- [x] credential欠落時に`status=unavailable`を返し、Open UIにunknownと表示するfail-safeを実装・mainへ統合。coverageをゼロに置換しない。
- [ ] build 820由来のMixpanel receiptが取れた後、preview aggregate→HTML値→production JSON→hydrated Open画面を同じ期間・分母で照合する。現行production JSONは`no_events`（0 view/exit、window 2026-10-30〜11-05）で、windowはbuild 820 upload前。`updated_at=02:37 JST`と`observed_at=02:52 JST`の鮮度差も解消する。deployment成功だけでは実データ表示の完了にしない。

## Task 5: 同一候補buildの全画面E2E動画と審査提出（G5）

**現在の状態（2026-11-08 03:05 JST）:** ASC CLI readbackは1.9.8/build 820=`VALID`、versionにbuild 820が紐付き、最新review submission `46f41ee2-5e57-4b09-8dd6-98a890b7a0f7`=`WAITING_FOR_REVIEW`。Xcode Cloud run #820 source `1555a020ece274ee68bc2587d161f44f019e1ac4`はPR #9272の祖先を含み、PR #9289のMixpanel一本化・18画面funnelを含む。Xcode Cloud Archive action成功、TestFlight External Testing actionはApple beta review submission errorで失敗。最終App Store export IPAのInfo.plistはbundle=`ai.anicca.app.ios`、version=`1.9.8`、build=`820`で、Mixpanel resourceあり。Open latest export windowはbuild 820 upload前で`no_events`。Mixpanel実receiptと同一build E2E/videoは未完了。状態の正本は統合SSOT。

**Build経路・実測:** ローカルXcode/`xcodebuild`を使わず、既存のXcode Cloud run #820（ID `22633fcf-fc26-4247-b86d-64b18c5c0c97`）をASC CLIでreadbackした。source SHAは`1555a020ece274ee68bc2587d161f44f019e1ac4`、Archive action=`SUCCEEDED`、build 820=`VALID`。同runのfinal App Store export IPAはASC build 820とbundle/version/buildが一致し、Mixpanel resourceと非空・非placeholderの`MIXPANEL_TOKEN`設定を含む（値は表示しない）。中間xcarchiveはInfo.plist=`817`だが、final ExportOptionsとIPA/ASCは`820`。buildは存在するが、同一build E2E動画は未作成。

**過去のG5失敗・資源記録:** candidate run/build 819（source `0f87589abfe38eaa8e7d2853a164ee01780496b3`）は`ci_post_clone.sh`が`ANICCA_PRODUCTION_XCCONFIG_B64`未設定で終了しartifactなし。過去のbrowser preflightは12 GiBを要求し、当時の空き容量は7.4 GiBだった。これは過去の測定で現在値ではなく、現在cursorでもない。現在の公式candidateはbuild 820。

- [x] ASC CLI read-onlyで現行状態を再確認: 1.9.8/build 820=`VALID`、review submission `46f41ee2-5e57-4b09-8dd6-98a890b7a0f7`=`WAITING_FOR_REVIEW`、前submission `9fa35898-1eee-44ce-942b-630780d9133b`=`COMPLETE`。
- [x] ASC review doctorを実行。唯一のblocking項目は旧submissionのreview item削除。15 warningsのうちsubscription `6758591116`（productId `Anicca`）とconsumable IAP `6755617833`（productId `ai.anicca.app.ios`）が`MISSING_METADATA`。
- [x] RevenueCat read-only APIのcurrent offering=`anicca_live_20261030`が`.monthly.b`/`.yearly.b`を使い、ASCで両SKUが`APPROVED`・$14.99/月・$59.99/年であることを照合。missing-metadataの`Anicca` subscriptionと`ai.anicca.app.ios` consumable IAPはcurrent offeringに含まれないため、ASC商品設定は変更しない。
- [ ] `asc review doctor`を最終candidate/metadata準備後に再実行し、blockingを0にする。optional promotional-image/keyword warningsと本番審査を妨げるmetadata不足を区別する。
- [ ] agreed UI/UXの全screen/overlay/state/localeをscreen inventoryに対応付け、onboarding→first affirmation→notification optional→paywall/close→feed→swipe→like/save/share→reminders/settings→restore/purchase flowのcoverageを定義する。
- [x] PR #9289 merge sourceからXcode Cloud run #820を作成し、ASC CLIでrun/build/source SHAをreadback。latest build 820=`VALID`、source SHA=`1555a020ece274ee68bc2587d161f44f019e1ac4`。
- [x] Xcode Cloud App Store export IPAを取得し、bundle/version/build=`ai.anicca.app.ios`/1.9.8/820、Mixpanel resource、非空・非placeholderの`MIXPANEL_TOKEN`設定を確認。中間archiveのInfo.plist build 817はExportOptions/IPA/ASCの820と異なるため、最終packageにはApp Store export IPAとASC readbackを採用。
- [x] Mac Mini Simulatorのbuild 819でMaestro 6 flows 6/6 PASS。JUnitは`/tmp/anicca-g4-simulator-20261107/maestro-full-e2e.xml`。これは署名candidateとのsource一致を証明しない。
- [x] YouTube限定公開動画を公式readback。初回UX（1:50）https://www.youtube.com/watch?v=n6nFFNuO2wg、通知routing（0:27）https://www.youtube.com/watch?v=LXw6enH20c0、6-flow E2E（4:20）https://www.youtube.com/watch?v=Wr0YQv0Gblk。3本ともSimulator build 819で、署名candidate一致は未証明。
- [ ] 全screen/flow inventoryを署名candidateで実行・録画し、動画/screenshots/JUnitを同一build/source SHAへ結び、録画を再生確認する。
- [ ] Mixpanel candidate receipt、Open preview/live aggregate、same-candidate video、ASC metadata/IAP/privacyを揃える。実端末APNs試験はユーザー指示で省略し、Simulator routingと区別する。purchase/trial/restoreの到達範囲と限界も記録する。
- [ ] G4/G4.1/G5の未完受入条件を満たす。review submission `46f41ee2-5e57-4b09-8dd6-98a890b7a0f7`は既に`WAITING_FOR_REVIEW`なので、この作業で取消し/重複提出をせず、実測と既存審査対象buildを照合して結果をSSOTへ残す。Appleの審査結果は別状態。

## Task 6: 全アプリ計測とOpen全体（日次履歴・国・流入・課金）（G6/G7）

**Files:** `apps/life-manager/scripts/{marketing-asc-acquisition,marketing-revenuecat-subscriptions,marketing-product-summary}.js` と対応test、`skills/earn/marketing-engine/registry/products/*.json`。Openの公開側は実deploymentのrepo/path/ownerを照合してから同ownerへ接続する。

**Consumes:** 公式出荷inventory、ASC reports、RevenueCat、product event、campaign registry。**Produces:** app/date/source/cohort/status/coverage付き履歴と既存Openの実データ表示。

- [ ] 全出荷inventoryとsource bindingを照合。5アプリ以外も存在/出荷/接続を確定する。
- [ ] missing day、閾値非提供、update/redownload混入、late revision、Honne欠測とAnicca継続、未成熟retention、refund/duplicate receiptのfixtureを先に追加して失敗を確認する。
- [ ] 既存collectorとproduct-pack入力を修復し、履歴/revision・nullable metric・分母/UTC/cohort/通貨を保つ。rateを作れないsourceはcountと理由を表示する。
- [ ] `node --test apps/life-manager/scripts/marketing-asc-acquisition.test.js apps/life-manager/scripts/marketing-revenuecat-subscriptions.test.js apps/life-manager/scripts/marketing-product-summary.test.js`。Expected: 全PASS、未接続sourceを0へ変換しない。
- [ ] Open ownerの公開経路へ結び、native scheduleの新snapshotと公開グラフ/時刻/狭幅をreadback。dashboard headerだけの更新を成功にしない。
- [ ] source acceptance→commit/push→review/CI/main→既存release経路→自然run/readback。G6/G7の状態を統合SSOTだけへ更新する。

## Task 7: 配信接続・実験・無人改善・他アプリ（G8〜G10）

**Files:** 既存 `marketing-product-summary.js`、`tiktok-metrics-due.js` とtests、product/campaign registry、確認済みapp deep-link handler、`config/loop-registry.json`、既存の実deployment/runbook。変更前に `skills/loop-development/SKILL.md` と現runtime owner/callerを読む。

**Consumes:** 日次履歴、stable content/campaign/quote ID、experiment assignment/exposure、現release/ASC状態。**Produces:** 配信→製品→指標→一改善→検証/動画→審査→公開の繰り返しと、他アプリの個別activation契約。

- [ ] install済み/未install/unknown campaign・未知quoteのdeep-link回帰、割付安定/SRM/欠測/成熟不足/重複wake/審査待ち/却下のfixtureを先に書き失敗を確認する。
- [ ] supported campaign/deep-linkを接続し、specの統計契約を満たす一実験を定義する。hard/soft・価格・trialは別仮説、baseline・MDE・必要人数・期間・guardrail・停止規則を開始前に記録する。
- [ ] 既存日次/週次処理と有限agent実行を設定し、Mobile Product Growth Ownerと配信/dashboard ownerの責任を固定する。OpenFaaS/Hermesは不足が実証された時だけ公式機能を調べて判断する。
- [ ] lifecycle registry/loop contractの既存検証と上記fixtureを実行。Expected: 欠測/標本不足は未判定、no-changeは根拠付き、審査待ちやunknown effectの重複submitなし。
- [ ] accepted/main由来releaseを所有者確認後に適用。自然wake→receipt→start→結果→dashboard、次の自然runの重複effect0を確認する。却下回復は実却下が無ければ隔離fixtureで検証し、live実績とは区別する。
- [ ] Aniccaで通った共通schema/取得/運用をHonne等へ展開。アプリごとのactivation/価値/課金を記述し、欠測分離と全inventory coverageを確認する。
- [ ] 全体の実施証拠・未確認の外部依存・profit/MRRの達成状況を統合SSOTへ残す。loop稼働を売上成長と読み替えない。

## 文書の共有・実行再開

この計画とspecは必ず同じcommitを参照する。再開者は統合SSOTのcursorとGit履歴を読み、完了済みtaskを再実行しない。Muse/Grokへ渡す際はrepo・branch・commit・spec/plan/SSOTのリンク・現在cursor・所有範囲を含める。チャットへの記載だけ、ローカル保存だけ、送信だけを共有完了にしない。
