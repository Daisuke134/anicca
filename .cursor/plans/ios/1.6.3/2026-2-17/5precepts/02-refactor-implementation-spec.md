# Anicca 1.6.2 Five Precepts - Refactor & Implementation Spec

## 1. As-Is Snapshot (current codebase)

現行実装の主要事実:

1. Onboardingは `welcome -> struggles -> liveDemo -> notifications -> paywall`（ソフト導線残存）
2. PaywallにカスタムXがあり、無料遷移ルートが存在
3. 通知タップで `NudgeCardView` が fullScreenCover 表示
4. `ProblemType` は13種
5. 文言在庫は `staying_up_late=21`, その他 `14`（EN/JA共通）
6. LLM fetch (`LLMNudgeService`) と `/api/mobile/nudge/today` が有効
7. Free系サービス (`FreePlanService`) が残存

## 2. Target Architecture

### 2.1 iOS flow

1. `OnboardingStep`: `welcome`, `notifications` の2ステップのみ
2. welcome CTAで通知許可を直接トリガー
3. 通知結果後、即 hard paywall（dismiss不可）
4. 購読成功で main

### 2.2 Main screen

1. 表示コンテンツを1ボタンに限定
2. `isActiveSubscriber == true`: `Cancel Subscription`
3. `isActiveSubscriber == false`: `Resubscribe`
4. 問題一覧/追加シート/デバッグNudge UIを削除

### 2.3 Notification runtime

1. `FivePreceptType`（新規）で5分類化
2. `ProblemNotificationScheduler` を `PreceptNotificationScheduler` に改名
3. 通知タップ時はカード表示しない
4. tap時は `MainTabView` を開くだけ（必要なら `selectedRootTab` セット）

## 3. iOS File-Level Change Plan

### 3.1 Onboarding

1. `aniccaios/aniccaios/Onboarding/OnboardingStep.swift`
   - `struggles/liveDemo` を削除
   - migrationは `raw=1,2,3` を `notifications` へ寄せる
2. `aniccaios/aniccaios/Onboarding/OnboardingFlowView.swift`
   - Struggles/Demoの分岐削除
   - `advance()` を2ステップ化
   - paywall overlayのXボタン削除
   - `handlePaywallDismissedAsFree()` 削除
3. `aniccaios/aniccaios/Onboarding/WelcomeStepView.swift`
   - 文言を固定:
     - Title: `Welcome to Anicca`
     - Subtitle: `Follow 5 Precepts for a better life`
     - CTA: `Enable Notifications`
   - 復元導線は維持
4. 削除候補
   - `aniccaios/aniccaios/Onboarding/StrugglesStepView.swift`
   - `aniccaios/aniccaios/Onboarding/DemoNudgeStepView.swift`

### 3.2 Main/UI

1. `aniccaios/aniccaios/MainTabView.swift`
   - `pendingNudgeCard` fullScreenCover削除
   - upgrade paywall誘発ロジック削除
2. `aniccaios/aniccaios/Views/MyPathTabView.swift`
   - 問題一覧、追加、デバッグ、アカウント危険操作を別画面へ退避
   - 1ボタンUIへ簡素化
3. 削除候補
   - `aniccaios/aniccaios/Views/NudgeCardView.swift`
   - `aniccaios/aniccaios/Views/NudgeCardContent.swift`
   - `aniccaios/CardScreenshotGenerator/Sources/ExportableNudgeCardView.swift`

### 3.3 Notifications

1. `aniccaios/aniccaios/Models/ProblemType.swift`
   - 新 `FivePreceptType.swift` に置換
2. `aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift`
   - precept版へ置換
   - `userInfo` の detailKey/variantIndex 依存を削る
3. `aniccaios/aniccaios/AppDelegate.swift`
   - 通知タップ時 `AppState.shared.showNudgeCard(...)` 削除
4. `aniccaios/aniccaios/Models/NudgeContent.swift`
   - NudgeCard専用モデルとして不要化（削除または縮退）

### 3.4 Subscription/Paywall

1. `aniccaios/aniccaios/Onboarding/OnboardingFlowView.swift`
   - hard paywall 100%（Xなし、dismiss不可）
2. `aniccaios/aniccaios/Views/MyPathTabView.swift`
   - free向け `Subscribe` の文言を `Resubscribe` に変更
3. `aniccaios/aniccaios/Services/AnalyticsManager.swift`
   - `onboardingPaywallDismissedFree`, `upgradePaywallPurchased` の削除

### 3.5 AppState cleanup

1. `aniccaios/aniccaios/AppState.swift`
   - `pendingNudgeCard`, nudge card counters, monthly nudge reset keys削除
   - `canReceiveNudge` を購読状態で fail-close 管理

### 3.6 Localization

対象: `aniccaios/aniccaios/Resources/{en,ja,es,fr,de,pt-BR}.lproj/Localizable.strings`

1. onboarding新文言
2. 5 precepts の title/hook 追加
3. 13 problem keys の段階的削除
4. `live_demo_*`, `nudge_*_detail_*` の削除

## 4. Backend/API Change Plan

1. `apps/api/src/jobs/generateNudges.js`
   - LLM分岐を停止
   - `generateRuleBasedNudges` のみ使用
2. `apps/api/src/jobs/nudgeHelpers.js`
   - `shouldUseLLM`, `generateWithFallback` を削除候補
3. `apps/api/src/routes/mobile/nudge.js`
   - `/today` を非推奨化（iOSから未使用にする）
4. DBの `problem_nudge` subtype を5 preceptsへ移行

## 5. Migration Rules (data)

### 5.1 Existing users

1. 旧 `userProfile.struggles` は無視
2. 初回起動時に preceptsを全選択状態で保存
3. 旧統計（problemType単位）は互換維持不要（別KPIへ）

### 5.2 Notification pending cleanup

1. 旧 identifier `PROBLEM_*`, `free_nudge_*`, `NUDGE_MAIN_*` を全削除
2. 新 identifier `PRECEPT_<type>_<hour>_<minute>_d<offset>` へ移行

## 6. Test Plan

### 6.1 Unit Tests

1. `OnboardingStepMigrationTests` を2ステップ版に更新
2. `ProblemTypeTests` を `FivePreceptTypeTests` に差し替え
3. 通知重複テスト（30日 x 3/日 = 90 unique / precept）
4. hard paywall dismiss不可テスト

### 6.2 Maestro

更新対象:

1. `aniccaios/maestro/onboarding/01-onboarding.yaml`
2. `aniccaios/maestro/onboarding/03-soft-paywall.yaml`（削除）
3. `aniccaios/maestro/nudge/*` のNudgeCard依存シナリオ（削除）

新規シナリオ:

1. onboarding_2step_hard_paywall.yaml
2. subscribe_then_main_single_button.yaml
3. cancel_then_resubscribe_button_only.yaml

## 7. Acceptance Criteria (release gate)

1. 初回起動からpaywall到達まで2タップ以内
2. paywallを閉じて無料利用に進めない
3. 非購読時に通知が1件も配信されない
4. 通知タップでカードが出ない
5. mainにボタンが1つのみ表示される
6. 5 precepts各90文面が6言語で存在する（合計2700 hooks）
7. 30日間で同文面重複ゼロ（precept内）

## 8. Execution Order

1. Onboarding/Paywall hard化
2. Main画面単機能化
3. NudgeCard除去
4. FivePreceptType導入 + scheduler置換
5. 文言在庫90x5x6投入（EN/JA/ES/FR/DE/PT-BR）
6. LLM/API cleanup
7. テスト更新
