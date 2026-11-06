# Anicca iOS Product Growth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task. チェック欄は実行手順の参照であり、順序・完了状態は統合SSOTだけに記録する。

**Goal:** Aniccaの初回製品改善を実機能・Maestro動画・審査提出まで届け、その後に全アプリの計測・Open・配信連携・無人改善を閉じる。

**Architecture:** 初回版は既存SwiftUI/UIKit、StoreKit/RevenueCat、Mixpanel/PostHogを修正する。後続は既存collector/registry/release/公開dashboardのownerへ接続し、第二のruntimeや分析基盤を新作しない。

**Tech Stack:** SwiftUI、UIKit、Swift focused tests、Maestro、APNs、RevenueCat、PostHog、Mixpanel、既存Life Manager scheduler/台帳、ASC CLI、Xcode Cloud。

**Spec:** `docs/superpowers/specs/2026-11-06-anicca-ios-product-growth-design.md`

**パスの基準:** `apps/`・`docs/`・`config/`・`skills/`で始まるpathはrepo基準。それ以外のiOS関連path（`aniccaios/`・`aniccaiosTests/`・`maestro/`・`fastlane/`・`scripts/`・`README.md`）は `apps/mobile/anicca-ios/` 基準。コマンドの実行cwdはrepo rootとする。

## Global Constraints

- 現在の実行範囲はG1〜G5。実装・Maestro実製品動画・審査提出まで進め、G6以降のloop/dashboardは起動しない。
- 実装順と状態は統合SSOTの `ANICCA-PRODUCT-GROWTH`、初回G1〜G5、後続G6〜G10。
- source=`Daisuke134/life-manager`、app=`apps/mobile/anicca-ios`、既存private configとowner/leaseを使用。
- 最小回帰のRED→GREEN、正本mainから署名build、公式readback。アプリのPackage.swiftはmacOS card生成用でありiOS検証の代替にしない。
- UI mockのデモ値を本番へ固定しない。初回soft paywall、現行購入権限/各対応言語の動作を維持。
- ダッシュボード/公開exportの別owner、配信owner、共有profile、他者のstateへ独断で同時変更しない。
- 容量不足は所有者を確認した再生成可能な不要物を整理して解消し、保存/pushを完遂する。
- App Reviewでは既存のASC/Xcode Cloud署名build 818を使い、現在のG5 cursorにローカルXcode/xcodebuildは使わない。
- App Review提出前に既存Simulator E2E動画2本をYouTube限定公開で提示する。動画はcandidate build 817であり、build 818との同一binary証拠ではない。

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
- [ ] 通知navigationのproduction sourceを `swiftc` で直接compileする `scripts/tests/QuoteNavigationTests.swift` と既存の通知/保存focused testsを実行。Expected: 新規回帰と既存通知/保存testがPASS。Maestro連続swipeはTask4で同じSHAを使用する。follow-upではローカルXcode project buildを使わず、署名buildは既存Xcode Cloud経路で行う。
- [ ] source acceptance→fetch→commit/push。実機APNsが未確認なら未確認と記録し、injection成功で代替しない。

## Task 3: 行動・課金計測の正確化（G4）

**Files:** `aniccaios/Services/{AnalyticsManager,SubscriptionManager}.swift`、`AppDelegate.swift`、Task1/2のscreen/action caller、関連XCTest。product設定/秘密値はrepo外。

**Consumes:** stable anonymous/customer ID、screen/quote/notification ID、StoreKit transaction/RevenueCat entitlement。**Produces:** specのevent契約、重複しない受信、価格不明時null/reason、通貨/receipt付き課金観測。

- [ ] SDK initialization・各caller・identify/reset・PostHog flag/exposure経路と本番受信先を照合する。
- [ ] 同一screen再描画、callback再送、restore、trial、不明価格、通貨違いをfixtureにし、二重売上と9.99捏造を防ぐ失敗testを書く。
- [ ] 既存eventを再利用して両分析経路を接続する。購入をreceiptで識別し、raw text/秘密値を送らず、internal/test buildを分離する。
- [ ] focused testとサービス側のテストsession受信を照合する。Expected: 正しいID/property、event重複0、purchase/restore/trialの区分が一致。receipt未接続はmissingとして残す。
- [ ] diff→fetch→commit/push。SDK導入/ローカルlogだけでは計測完了にしない。

## Task 4: Maestro動画・レビュー・署名・審査提出（G5）

**状態:** 完了。build 818を使う1.9.8はASCで`WAITING_FOR_REVIEW`。Appleの承認・公開待ち。

**実施結果（2026-11-06）:**

- [x] 既存iOS 26.5 Simulator Maestro 13/14録画を確認。初回体験と通知フロー動画を再生確認。いずれもcandidate build 817で、build 818/PR #9282に結び付く同一binary証拠ではない。実端末APNsの検証とは扱わない。
- [x] PostizのYouTube連携「Daily Affirmation App - Anicca」へ2本を限定公開で投稿し、YouTube `releaseURL`・`PUBLISHED`・`type=unlisted`をreadback。初回体験: https://www.youtube.com/watch?v=88N3zsKZUJM / 通知: https://www.youtube.com/watch?v=J005BFtO88U。動画説明にSimulator candidate build 817と明記。
- [x] App=`6755129214`の既存提出ID `cb6fa5a3-c350-482d-9ca7-369be6785249`を1.9.7/build 816/`WAITING_FOR_REVIEW`と照合して取下げ。同じIDのGETは`COMPLETE`、item `REMOVED`。取下げ前の1.9.7は`DEVELOPER_REJECTED`。
- [x] Appleは未公開1.9.7 version objectがあるため1.9.8の新規作成を拒否し、既存版の番号更新を指示。version ID `224f1d6d-e7b4-4dc7-9258-111e67de7363`を1.9.8へ変更、build `7cfb4f37-680c-447d-873a-7f8eb54a0baf` (818)を添付。version/build readback一致、build=`VALID`/`APP_STORE_ELIGIBLE`。
- [x] 審査メモを1.9.8/build 818向けに更新。版検証 errors=0/blocking=0/warnings=15。App=`6755129214`、version ID=`224f1d6d-e7b4-4dc7-9258-111e67de7363`、build 818で提出し、新submission ID `306c7696-bc5d-4aa2-b82c-1fc0a07d253c`の`WAITING_FOR_REVIEW`、item `READY_FOR_REVIEW`を公式readback。submit時、旧`Anicca Monthly Plan`は`MISSING_METADATA`のため今回の審査対象から除外されるとの警告あり。

**この提出で未確認:** PR #9282と同じbuild 818のE2E録画、実端末APNs、実購入/有料restore、分析service側event受信。App Privacy公開状態もCLI doctorでは確認できない。詳細・次のTODOは統合SSOT `ANICCA-PRODUCT-GROWTH` のG2/G4を参照。今回のASC提出にローカルXcode/xcodebuildは使用しない。

## Task 5: 全アプリ計測とOpen（日次履歴・国・流入・課金）（G6/G7）

**Files:** `apps/life-manager/scripts/{marketing-asc-acquisition,marketing-revenuecat-subscriptions,marketing-product-summary}.js` と対応test、`skills/earn/marketing-engine/registry/products/*.json`。Openの公開側は実deploymentのrepo/path/ownerを照合してから同ownerへ接続する。

**Consumes:** 公式出荷inventory、ASC reports、RevenueCat、product event、campaign registry。**Produces:** app/date/source/cohort/status/coverage付き履歴と既存Openの実データ表示。

- [ ] 全出荷inventoryとsource bindingを照合。5アプリ以外も存在/出荷/接続を確定する。
- [ ] missing day、閾値非提供、update/redownload混入、late revision、Honne欠測とAnicca継続、未成熟retention、refund/duplicate receiptのfixtureを先に追加して失敗を確認する。
- [ ] 既存collectorとproduct-pack入力を修復し、履歴/revision・nullable metric・分母/UTC/cohort/通貨を保つ。rateを作れないsourceはcountと理由を表示する。
- [ ] `node --test apps/life-manager/scripts/marketing-asc-acquisition.test.js apps/life-manager/scripts/marketing-revenuecat-subscriptions.test.js apps/life-manager/scripts/marketing-product-summary.test.js`。Expected: 全PASS、未接続sourceを0へ変換しない。
- [ ] Open ownerの公開経路へ結び、native scheduleの新snapshotと公開グラフ/時刻/狭幅をreadback。dashboard headerだけの更新を成功にしない。
- [ ] source acceptance→commit/push→review/CI/main→既存release経路→自然run/readback。G6/G7の状態を統合SSOTだけへ更新する。

## Task 6: 配信接続・実験・無人改善・他アプリ（G8〜G10）

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
