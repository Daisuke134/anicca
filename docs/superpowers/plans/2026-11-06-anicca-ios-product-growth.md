# Anicca iOS Product Growth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task. チェック欄は実行手順の参照であり、順序・完了状態は統合SSOTだけに記録する。

**Goal:** Anicca iOSの画面別計測をMixpanel一本で本番運用し、既存Openで確認できるようにして、同一候補buildの全画面Maestro動画を提示した後にだけ審査へ提出する。

**Architecture:** iOSは既存SwiftUI/UIKit・StoreKit/RevenueCat・Mixpanelを使い、PostHogの重複経路を除く。Aniccaの集計はLife Manager既存product summaryから既存Open snapshotへつなぎ、dashboard ownerの`anicca-products` repoで表示する。第二の分析基盤/dashboard/runtimeを作らない。

**Tech Stack:** SwiftUI、UIKit、Swift focused tests、Maestro、APNs、RevenueCat、Mixpanel、既存Life Manager collectors、anicca-products Open snapshot、ASC CLI、Xcode Cloud（署名buildのみ）。Xcode UIは使わない。

**Spec:** `docs/superpowers/specs/2026-11-06-anicca-ios-product-growth-design.md`

**パスの基準:** `apps/`・`docs/`・`config/`・`skills/`で始まるpathはrepo基準。それ以外のiOS関連path（`aniccaios/`・`aniccaiosTests/`・`maestro/`・`fastlane/`・`scripts/`・`README.md`）は `apps/mobile/anicca-ios/` 基準。コマンドの実行cwdはrepo rootとする。

## Global Constraints

- 現在順はG2残件→G4 Mixpanel一本化→G4.1 Anicca funnelをOpenへ表示→G5同一candidate E2E/動画/審査提出。G1/G3は検証済みとして再利用する。
- G1〜G4/G4.1と全画面同一build E2Eが実証されるまでApp Review submissionを作らない。実装順/状態の唯一の正本は統合SSOT `ANICCA-PRODUCT-GROWTH`。
- G6/G7全アプリ展開とG8〜G10自動改善はその後へ保持する。G4.1はAniccaだけの提出前必須slice。
- source=`Daisuke134/life-manager`、app=`apps/mobile/anicca-ios`、既存private configとowner/leaseを使用。
- 最小回帰のRED→GREEN、正本mainから署名build、公式readback。アプリのPackage.swiftはmacOS card生成用でありiOS検証の代替にしない。
- UI mockのデモ値を本番へ固定しない。初回soft paywall、現行購入権限/各対応言語の動作を維持。
- ダッシュボード/公開exportの別owner、配信owner、共有profile、他者のstateへ独断で同時変更しない。
- 容量不足は所有者を確認した再生成可能な不要物を整理して解消し、保存/pushを完遂する。
- App Store Connectの提出/取消/状態確認はASC CLIで行う。署名済みartifactの作成は既存Xcode Cloud、Maestro実行/録画はMac MiniのSimulatorを使い、Xcode UIは開かない。
- 既存YouTube動画2本はcandidate build 817であり、build 818と同一binaryの証拠ではない。変更後candidateと同じsource/buildに結び付く全画面動画を新しく作成して提出前に提示する。
- 1.9.8/build 818のsubmissionは取消済み。version state `DEVELOPER_REJECTED`とdoctorの`review.submission.removed_items_only`は現状 readback。分析/動画条件を満たすまで再提出しない。

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

- [ ] 全screen inventoryをproduction codeへ対応付け、現在のevent/caller、paywallの重複、復元経路、匿名ID/identify/reset、PostHog直接呼出しを記録する。
- [ ] Mixpanel Swift SDKのfeature flags要件（公式docsは6.4.0以上）を満たすstable releaseへpinし、PostHog Package/Info.plist config/SDK captureを除去する。Experiments利用可否・MEU allowance・project regionはMixpanel accountでreadbackする。
- [ ] 同一screen再描画、戻る/進む、background/resume、duplicate callback、restore、trial、不明価格、通貨違い、offline再送を隔離fixtureにし、screen重複・二重売上・推定収益の混入を防ぐ。
- [ ] screen/flow/activation/notification/paywall/product/purchase/trial/restore/exposureにevent/property contractを付け、raw affirmation text/PII/secretを送らず内部buildを識別する。画面終了は明示的遷移だけを送り、OS killは次step観測窓によるdrop-off推定とラベルする。
- [ ] focused tests後にMixpanel側で同じtest identityのevent・properties・build/locale/variant・時刻をreadbackし、同一event/transaction重複0を照合する。local log/SDK configだけでは完了にしない。
- [ ] source acceptance→fetch→commit/push。provider receiptと根拠をSSOTへ残す。

## Task 4: Aniccaの画面別funnelを既存Openへ接続（G4.1）

**iOS source:** `apps/mobile/anicca-ios/aniccaios/Services/AnalyticsManager.swift`と各screen caller（Task3）。**集計source:** `apps/life-manager/scripts/marketing-product-summary.js`、対応test、`tenants/dais-local/product-packs/metrics/product-analytics/anicca-ios.json`のcontract。**公開owner:** `Daisuke134/anicca-products`の`apps/landing/public/open/index.html`、生成`data.json`、`.github/workflows/netlify-deploy.yml`。現在のASC collector`apps/landing/scripts/open-app-store-analytics.mjs`はstore acquisitionのみなので、Mixpanel event collectorと混同しない。

**Consumes:** Mixpanel aggregate、App Store Connect/RevenueCatの公式cohort/収益、app/date/locale/campaign/release/experiment dimensions。**Produces:** 公開個人データを含まないAnicca screen funnel panelと日次snapshot。

- [ ] 現行Netlify deployで`out/open/data.json`を作る全step・secret scope・snapshot ownerを読み、Mixpanelのserver-side read経路と安全なCI credential存在を確認する。public HTML/JSへAPI secretを含めない。
- [ ] 既存`marketing-product-summary.js`のproduct-pack inputがMixpanel query/export resultを安全に表現できるか確認する。既存sourceへ最小接続し、新runtime/schedulerを作らない。利用可能なAPI/plan/権限が無ければ不足credential/owner/pathをcursorに残し、measured値を捏造しない。
- [ ] Openの`data.json` contractに`product_analytics.anicca_ios` aggregateを加え、observed_at/data_from/data_to/status/coverage/numerator/denominator/cohort/window/locale/source/release/variantとnullable valueを保持する。
- [ ] `index.html`にfunnel人数・率・分母、screen順/drop-off、first valueまでの時間、notification/purchase/trial/restore、成熟D1/D7/D30、country/storefront/locale/campaign/release/variant filterを既存デザインで表示する。未成熟・threshold/欠測はunknownと理由を出す。
- [ ] snapshot builder・schema testで0/unknown、partial day、late correction、少数cohort、二重event、currency、privacy thresholdを検証する。個人ID・affirmation本文・credentialは公開JSONに含めない。
- [ ] netlify deploy previewだけで終わらせず、既存のowner/release経路でsource acceptance後に公開し、live `/open/`と`data.json`の表示・source freshness・denominator・狭幅layoutを公式readback。G4.1結果をG5条件にする。

## Task 5: 同一候補buildの全画面E2E動画と審査提出（G5）

**状態:** 1.9.8/build 818の提出は取消済み。再提出は禁止条件がすべてPASSするまで行わない。現ASC stateはversion=`DEVELOPER_REJECTED`、build 818=`VALID`、旧submission `306c7696-bc5d-4aa2-b82c-1fc0a07d253c`=`COMPLETE`/item=`REMOVED`。

**Xcode Cloud:** enabled `Default` workflowはlockedで`main` branchだけを受け付け、PR/manual branch conditionは空。Draft PR #9289のApple SCM PR IDを使った起動はbranch未登録で拒否され、buildは作成されなかった。既存`Untitled Workflow`はdisabled/unlocked、schemeは`aniccaios`だがcontainer pathが旧値`aniccaios/aniccaios.xcodeproj`。次はこのworkflowを現行project pathと今回のfeature branchへ限定して一回だけ使い、run後にdisabledへ戻す。Xcode Cloud environment variablesは公開APIに現れず、Apple web sessionは2FA SMSをMac Messagesで取得できず未認証。Mixpanel token注入/readbackは未確認で、build成功を本番tracking成功と扱わない。

**最新実行:** candidate run/build 819（source `0f87589abfe38eaa8e7d2853a164ee01780496b3`）は`ci_post_clone.sh`が`ANICCA_PRODUCTION_XCCONFIG_B64`未設定で終了し、artifactを生成しなかった。ASC Web CLIのsecret設定に登録済み`mobile-release:dais` browser sessionが必要だが、起動preflightは空き12 GiBを要求し、現在7.5 GiB。非稼働のMaestro/XCTest一時結果13個（678 MiB）を削除済み。次cursorは再生成可能な一時artifactだけを追加調査してpreflightを満たし、identity lease経由でsecretを設定してcandidateを再実行すること。稼働中Chrome/Simulator、運用state、求人/納品証拠は保持する。

- [ ] `asc review doctor`の現在の`review.submission.removed_items_only`を読み、取消済みのblockerを将来のfresh submissionと混同しない。G2/G4/G4.1 gateが完了するまでsubmit API/commandを呼ばない。
- [ ] agreed UI/UXの全screen/overlay/state/localeをscreen inventoryに対応付け、onboarding→first affirmation→notification optional→paywall/close→feed→swipe→like/save/share→reminders/settings→restore/purchase flowのcoverageを定義する。
- [ ] 証拠承認前のmain統合を避け、今回の専用feature branch SHAからXcode Cloudで署名candidateを作る。ASC CLIでbuild/sourceをreadback。Mac Mini SimulatorでMaestroの全screen/flowを実行し、same candidate build/source SHAを含む動画・screenshots・JUnit/logを保存する。動画から各screenの挙動と離脱導線を再生確認する。Xcode UIは開かない。
- [ ] 動画はYouTube限定公開で、ユーザーへリンクを提出前に提示する。既存UX `https://www.youtube.com/watch?v=88N3zsKZUJM` と通知 `https://www.youtube.com/watch?v=J005BFtO88U` はcandidate build 817なので参考動画としてのみ扱う。
- [ ] Mixpanel test event receipt、Open live snapshot readback、実端末APNs/通知設定、purchase/trial/paid restore、screen coverageが同じ候補sourceで揃ったことを確認する。App Store IAP metadata/territory/price、privacy、review notesも再照合し、`Anicca Monthly Plan`の`MISSING_METADATA`警告を解消または対象外理由まで明示する。
- [ ] 証拠一式（Mixpanel受信、Open表示、同一build E2E動画、通知/購入/restore確認、ASC metadata）をユーザーへ提示し、明示承認を得る。承認前はASC submit・本番公開・main統合を行わない。
- [ ] 明示承認後だけASC CLIでversion/buildをvalidateして一度submitし、submission/version/buildの公式readbackが一致することを確認する。`WAITING_FOR_REVIEW`以降のApple判断は別状態。

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
