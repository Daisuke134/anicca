# ImpulseLog — 実装タスクリスト（tasks.md）

**作成日:** 2026-02-26

---

## PHASE 2: SCAFFOLD

- [ ] Xcode プロジェクト作成（bundle_id: com.anicca.impulselog）
- [ ] RevenueCat SDK を SPM で追加
- [ ] Mixpanel SDK を SPM で追加
- [ ] PrivacyInfo.xcprivacy 追加
- [ ] SwiftData コンテナ設定
- [ ] Localizable.strings (en/ja) 作成
- [ ] Assets.xcassets にアイコンプレースホルダー設定

## PHASE 3: BUILD

### モデル
- [ ] ImpulseLog.swift（SwiftData @Model）
- [ ] EmotionType.swift（enum）
- [ ] TriggerTag.swift（enum）

### サービス
- [ ] SubscriptionManager.swift（RevenueCat）
- [ ] NotificationService.swift（APNs）
- [ ] MixpanelService.swift
- [ ] LocalizationHelper.swift（OS言語判定）
- [ ] FreePlanService.swift（Free制限チェック）

### オンボーディング
- [ ] OnboardingWelcomeView.swift（accessibilityIdentifier: onboarding-welcome-cta）
- [ ] PainSelectionView.swift（accessibilityIdentifier: onboarding-pain-selection）
- [ ] LiveDemoView.swift（accessibilityIdentifier: onboarding-live-demo）
- [ ] NotificationPermissionView.swift（accessibilityIdentifier: onboarding-notifications-allow）

### メイン
- [ ] MainTabView.swift
- [ ] LogHomeView.swift（accessibilityIdentifier: log-home）
- [ ] QuickLogSheet.swift（30秒ログUI）
- [ ] ReportsView.swift（週次レポート）

### Paywall
- [ ] PaywallView.swift
  - accessibilityIdentifier: paywall_plan_monthly
  - accessibilityIdentifier: paywall_plan_yearly
  - accessibilityIdentifier: paywall_cta
  - accessibilityIdentifier: paywall_skip
  - accessibilityIdentifier: paywall_restore

### Settings
- [ ] SettingsView.swift（Privacy Policy + Terms リンク）

### テスト
- [ ] ImpulseLogModelTests.swift
- [ ] FreePlanServiceTests.swift
- [ ] LocalizationTests.swift
- [ ] ScreenshotTests.swift（UITests用）

### スクショ用セットアップ
- [ ] UITests ターゲット作成
- [ ] ScreenshotTests.swift（testScreenshot_Main / testScreenshot_Reports / testScreenshot_Paywall）
- [ ] docs/screenshots/scripts/extract_screenshots.py
- [ ] docs/screenshots/scripts/process_screenshots.py
- [ ] docs/screenshots/screenshots.yaml

## PHASE 3.5: PRIVACY POLICY & LANDING PAGE
- [ ] anicca.app/impulse-log/privacy/en をデプロイ
- [ ] anicca.app/impulse-log/privacy/ja をデプロイ
- [ ] anicca.app/impulse-log ランディングページをデプロイ
- [ ] URL生死確認

## PHASE 4: ASC APP SETUP
- [ ] Bundle ID 作成
- [ ] App Store Connect にアプリ作成
- [ ] Privacy Policy URL 設定（en-US + ja）
- [ ] サブスクリプショングループ作成
- [ ] Monthly サブスク作成
- [ ] Annual サブスク作成
- [ ] Availability 設定（175カ国）

## PHASE 4.5: RC OFFERINGS
- [ ] RevenueCat でプロジェクト作成
- [ ] Offerings 設定（default Offering）
- [ ] Package 追加（$rc_monthly + $rc_annual）

## PHASE 5: IAP PRICING
- [ ] 175カ国の価格設定（add_prices.py）
- [ ] 175件確認

## PHASE 6: IAP LOCALIZATION
- [ ] Monthly EN + JA ローカライズ
- [ ] Annual EN + JA ローカライズ

## PHASE 7: IAP REVIEW SCREENSHOT
- [ ] Paywall スクショ撮影
- [ ] Monthly + Annual にアップロード

## PHASE 8: IAP VALIDATE
- [ ] blocking = 0 確認
- [ ] READY_TO_SUBMIT 確認（Monthly + Annual）

## PHASE 9: APP ASSETS
- [ ] アプリアイコン生成（snapai）
- [ ] EN スクショ生成（screenshot-creator）
- [ ] JA スクショ生成（screenshot-creator）
- [ ] ASC にアップロード
- [ ] メタデータ入力

## PHASE 10: BUILD & UPLOAD
- [ ] fastlane gym でビルド
- [ ] ASC CLI でアップロード
- [ ] TestFlight 配布

## PHASE 11: PREFLIGHT GATE
- [ ] Greenlight チェック
- [ ] IAP 確認
- [ ] コード品質チェック
- [ ] URL確認
- [ ] スクショ確認

## PHASE 11.6: IAP SUBMIT
- [ ] Monthly WAITING_FOR_REVIEW
- [ ] Annual WAITING_FOR_REVIEW

## PHASE 11.5: APP PRIVACY（手動）
- [ ] ユーザーに手動設定依頼

## PHASE 12: SUBMIT
- [ ] App Store 提出
- [ ] WAITING_FOR_REVIEW 確認
