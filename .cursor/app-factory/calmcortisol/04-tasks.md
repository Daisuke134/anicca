# CalmCortisol — Implementation Tasks

## PHASE 2: SCAFFOLD
- [ ] Xcode プロジェクト作成 (`CalmCortisol` / bundle_id: com.anicca.calmcortisol)
- [ ] RevenueCat SDK を SPM で追加
- [ ] Mixpanel SDK を SPM で追加
- [ ] PrivacyInfo.xcprivacy を追加
- [ ] Localizable.strings (en + ja) 作成
- [ ] AppIcon.appiconset を Assets に配置
- [ ] Fastfile 作成 (test / build / release lanes)

## PHASE 3: BUILD
- [ ] BreathingType.swift モデル
- [ ] BreathingSession.swift モデル
- [ ] UserProfile.swift モデル
- [ ] SubscriptionManager.swift (RevenueCat)
- [ ] AnalyticsService.swift (Mixpanel)
- [ ] NotificationService.swift (APNs プロアクティブスケジュール)
- [ ] SessionStore.swift (UserDefaults)
- [ ] WelcomeView.swift
- [ ] PainSelectionView.swift
- [ ] DemoSessionView.swift (30秒体験)
- [ ] NotificationPermissionView.swift
- [ ] PaywallView.swift (RC Offerings + accessibilityIdentifiers)
- [ ] DashboardView.swift (コルチゾールバー + クイックスタート)
- [ ] BreathingSessionView.swift
- [ ] BreathingAnimationView.swift (円拡縮 Animation)
- [ ] PostSessionFeedbackView.swift
- [ ] SettingsView.swift (Privacy / Terms / Restore)
- [ ] ScreenshotTests.swift (XCUITest)
- [ ] Unit Tests: BreathingTypeTests.swift
- [ ] Unit Tests: SessionStoreTests.swift

## PHASE 3.5: PRIVACY POLICY デプロイ
- [ ] anicca.app/calmcortisol/privacy/en HTML 作成
- [ ] anicca.app/calmcortisol/privacy/ja HTML 作成
- [ ] anicca.app/calmcortisol LP HTML 作成
- [ ] URL 生存確認 (curl)

## PHASE 4: ASC APP SETUP
- [ ] fastlane produce create でアプリ登録
- [ ] APP_ID 取得
- [ ] Privacy Policy URL設定 (en-US + ja)
- [ ] サブスクグループ作成
- [ ] Monthly サブスク作成
- [ ] Annual サブスク作成
- [ ] availability set (Monthly + Annual)

## PHASE 4.5: RC OFFERINGS
- [ ] RC ダッシュボードでプロジェクト作成/確認
- [ ] Offering "default" 作成
- [ ] $rc_monthly / $rc_annual パッケージ設定
- [ ] Current に設定

## PHASE 5: IAP PRICING
- [ ] Monthly 175カ国 pricing 設定
- [ ] Annual 175カ国 pricing 設定
- [ ] 175件確認

## PHASE 6: IAP LOCALIZATION
- [ ] Monthly en-US ローカライズ
- [ ] Monthly ja ローカライズ
- [ ] Annual en-US ローカライズ
- [ ] Annual ja ローカライズ

## PHASE 7: IAP REVIEW SCREENSHOT
- [ ] シミュレータ起動 + Paywall まで遷移
- [ ] スクショ撮影 + JPEG変換
- [ ] Monthly にアップロード
- [ ] Annual にアップロード

## PHASE 8: IAP VALIDATE
- [ ] blocking = 0 確認
- [ ] Monthly READY_TO_SUBMIT 確認
- [ ] Annual READY_TO_SUBMIT 確認

## PHASE 9: APP ASSETS
- [ ] アイコン生成 (SnapAI + ImageMagick)
- [ ] スクショ EN 生成 (screenshot-creator)
- [ ] スクショ JA 生成
- [ ] ASC アップロード
- [ ] App Store メタデータ入力

## PHASE 10: BUILD & UPLOAD
- [ ] fastlane release 実行
- [ ] processingState = VALID 確認
- [ ] TestFlight ベータグループ配布

## PHASE 11: PREFLIGHT
- [ ] GATE 1: Greenlight blocking = 0
- [ ] GATE 2: IAP 全チェック
- [ ] GATE 3: Lorem/TODO 検索
- [ ] GATE 4: 外部URL生存確認
- [ ] GATE 5: スクショ数確認

## PHASE 11.5: APP PRIVACY (手動)
- [ ] ユーザーがASC WebでApp Privacy設定

## PHASE 11.6: IAP SUBMIT
- [ ] Monthly submit
- [ ] Annual submit
- [ ] 両方 WAITING_FOR_REVIEW 確認

## PHASE 12: SUBMIT
- [ ] asc submit create --confirm
- [ ] state = WAITING_FOR_REVIEW 確認
