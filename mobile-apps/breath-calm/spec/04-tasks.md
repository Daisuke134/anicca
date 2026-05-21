# BreathCalm — tasks.md (実装タスクリスト)

Generated: 2026-02-24

---

## PHASE 1: Validate Input

- [ ] 02-spec.md の全フィールド確認 (app_name, bundle_id, version, output_dir)
- [ ] price_monthly_usd / price_annual_usd 確認
- [ ] paywall.cta_text_en / ja 確認
- [ ] metadata EN+JA 全項目確認
- [ ] URLs (privacy_en/ja, terms, landing) 確認
- [ ] localization / supported_locales 確認

## PHASE 2: Scaffold

- [ ] Xcodeプロジェクト作成 (`/Users/cbns03/Downloads/anicca-project/breath-calm-app/BreathCalmios/`)
- [ ] Bundle ID設定: `com.aniccaai.breathcalm`
- [ ] Team ID設定
- [ ] RevenueCat SDK追加 (SPM)
- [ ] Mixpanel SDK追加 (SPM)
- [ ] PrivacyInfo.xcprivacy追加 (NSPrivacyAccessedAPICategoryUserDefaults)
- [ ] Localizable.strings (en + ja) 作成
- [ ] UITests ターゲット作成

## PHASE 3: Build (SwiftUI実装)

- [ ] Models: BreathingSession, SessionType, MoodEntry
- [ ] Services: SubscriptionManager, SessionManager, AudioManager, MixpanelService, NotificationManager
- [ ] Onboarding: WelcomeView, AnxietyLevelView, NotificationPermissionView
- [ ] Main: MainTabView, HomeView, HistoryView, SettingsView
- [ ] Session: PreSessionMoodView, BreathingSessionView, PostSessionMoodView, BreathingAnimation
- [ ] Paywall: PaywallView (5つのaccessibilityIdentifier必須)
- [ ] Free/Pro制限実装 (SessionManager + SubscriptionManager)
- [ ] バイノーラルビーツ音声ファイル追加
- [ ] ScreenshotTests.swift作成 (testScreenshot_Home, testScreenshot_Session, testScreenshot_Paywall)
- [ ] Makefile generate-store-screenshots ターゲット追加
- [ ] extract_screenshots.py + process_screenshots.py 追加

## PHASE 3.5: Landing Page

- [ ] `apps/landing/breath-calm/index.html` 作成
- [ ] `apps/landing/breath-calm/privacy/en/index.html` 作成
- [ ] `apps/landing/breath-calm/privacy/ja/index.html` 作成
- [ ] `apps/landing/breath-calm/terms/index.html` 作成 (Appleへリダイレクト)
- [ ] dev branch push → Netlify自動デプロイ
- [ ] URL生存確認 (privacy_en / privacy_ja)

## PHASE 4: ASC App Setup

- [ ] `asc apps create` でアプリ作成
- [ ] Privacy Policy URL設定 (en-US + ja 両方)
- [ ] Subscription Group作成 ("Premium")
- [ ] Monthly IAP作成 (`com.aniccaai.breathcalm.premium.monthly`)
- [ ] Annual IAP作成 (`com.aniccaai.breathcalm.premium.yearly`)
- [ ] Availability設定 (pricing前に必須)

## PHASE 4.5: RC Offerings Setup

- [ ] RC Dashboard でBreathCalmプロジェクト/アプリ追加
- [ ] Offering "default" 作成
- [ ] $rc_monthly / $rc_annual パッケージ追加
- [ ] Apple Product IDを紐付け
- [ ] Offeringを "current" に設定
- [ ] IAP Key AY9BT5R8NU 確認

## PHASE 5: IAP Pricing

- [ ] US価格ポイントID取得
- [ ] scripts/add_prices.py で175カ国全設定
- [ ] 175件確認

## PHASE 6: IAP Localization

- [ ] Monthly en-US localization
- [ ] Monthly ja localization
- [ ] Annual en-US localization
- [ ] Annual ja localization

## PHASE 7: IAP Review Screenshot

- [ ] シミュレータ起動 (iPhone 16 Pro Max)
- [ ] Maestro MCPでPaywall画面まで遷移
- [ ] スクリーンショット撮影 + JPEG変換 (1320×2868)
- [ ] Monthly / Annual両方にアップロード

## PHASE 8: IAP Validate (STOP GATE)

- [ ] `asc validate subscriptions` → blocking=0
- [ ] Monthly state = READY_TO_SUBMIT
- [ ] Annual state = READY_TO_SUBMIT

## PHASE 9: App Assets

- [ ] アイコン生成 (SnapAI + ImageMagick)
- [ ] ユーザー承認
- [ ] スクリーンショット生成 EN (screenshot-creator)
- [ ] スクリーンショット生成 JA
- [ ] ASCアップロード (EN + JA)
- [ ] メタデータ入力 (EN + JA)

## PHASE 10: Build & Upload

- [ ] `fastlane set_version version:1.0.0`
- [ ] `fastlane release`
- [ ] processingState = VALID 待機
- [ ] TestFlightベータグループに配布

## PHASE 11: Preflight Gate

- [ ] GATE 1: Greenlight CRITICAL=0
- [ ] GATE 2: IAP prices 175件 / screenshot存在 / READY_TO_SUBMIT
- [ ] GATE 3: Lorem/TODO/FIXME なし
- [ ] GATE 4: privacy_en / privacy_ja URL生存
- [ ] GATE 5: EN/JAスクリーンショット3枚以上

## PHASE 11.5: App Privacy手動設定

- [ ] ユーザーにASC Web手動設定を依頼
- [ ] ユーザー「完了」確認後フェーズ12へ

## PHASE 12: Submit

- [ ] VERSION_ID取得
- [ ] BUILD_ID取得
- [ ] `asc submit create --confirm`
- [ ] state = WAITING_FOR_REVIEW 確認
