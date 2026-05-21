# BreathReset Implementation Tasks

## PHASE 2: SCAFFOLD
- [ ] output_dir 作成: /Users/anicca/Downloads/breath-reset-app
- [ ] Xcode プロジェクト生成（BreathReset.xcodeproj）
- [ ] Bundle ID 設定: com.anicca.breathreset
- [ ] RevenueCat SDK を SPM で追加
- [ ] Mixpanel SDK を SPM で追加
- [ ] PrivacyInfo.xcprivacy 作成（NSPrivacyAccessedAPICategoryUserDefaults + CA92.1）
- [ ] Localizable.strings (en + ja) 作成
- [ ] Assets.xcassets/AppIcon.appiconset 設定

## PHASE 3: BUILD
### Models
- [ ] BreathingTechnique.swift（6種類定義）
- [ ] BreathingSession.swift（記録モデル）
- [ ] UserStats.swift（ストリーク計算）

### Services
- [ ] SubscriptionManager.swift（RevenueCat SDK統合）
- [ ] NotificationService.swift（9am/2pm/8pm通知）
- [ ] SessionStore.swift（UserDefaults保存）
- [ ] MixpanelService.swift（paywall_viewed等）

### Views
- [ ] WelcomeView.swift（オンボーディング1）
- [ ] ProblemView.swift（オンボーディング2: スライダー）
- [ ] SolutionView.swift（オンボーディング3）
- [ ] HomeView.swift（ホーム: 今日のセッション + ストリーク）
- [ ] SessionView.swift（呼吸セッションメイン）
- [ ] BreathingCircleView.swift（円アニメーション）
- [ ] TechniquePickerView.swift（呼吸法選択）
- [ ] StatsView.swift（統計画面）
- [ ] PaywallView.swift（RevenueCat + accessibilityIdentifier 5要素）
- [ ] SettingsView.swift（通知 + Privacy + Terms）
- [ ] ContentView.swift（TabView分岐）

### Tests
- [ ] BreathingTechniqueTests.swift（ユニットテスト）
- [ ] SessionStoreTests.swift（保存/読込テスト）
- [ ] SubscriptionManagerTests.swift（RC連携テスト）
- [ ] ScreenshotTests.swift（XCUITest: Main/Session/Paywall）

## PHASE 3.5: LANDING
- [ ] /breath-reset/privacy/en ページ作成 & Netlify デプロイ
- [ ] /breath-reset/privacy/ja ページ作成 & Netlify デプロイ
- [ ] URL生死確認（curl 200/301/302）

## PHASE 4: ASC
- [ ] Bundle ID 登録: asc bundle-ids create
- [ ] App作成: asc apps create
- [ ] Privacy URL 設定（en + ja）
- [ ] Subscription Group 作成
- [ ] Monthly / Annual Subscription 作成
- [ ] availability set（全テリトリー）
- [ ] primaryCategory 設定（HEALTH_AND_FITNESS）

## PHASE 4.5: RC
- [ ] RC Project: com.anicca.breathreset
- [ ] Offerings: default（monthly + annual）
- [ ] IAP Key 設定
- [ ] Mixpanel連携有効化

## PHASE 5: IAP PRICING
- [ ] add_prices.py 実行（175カ国）
- [ ] 175件確認

## PHASE 6: IAP LOCALIZATION
- [ ] Monthly EN + JA
- [ ] Annual EN + JA

## PHASE 7: IAP REVIEW SCREENSHOT
- [ ] シミュレータ起動
- [ ] Paywall画面遷移
- [ ] スクショ撮影 (1320×2868)
- [ ] Monthly + Annual アップロード

## PHASE 8: IAP VALIDATE
- [ ] blocking=0 確認
- [ ] warnings=0 確認
- [ ] READY_TO_SUBMIT 確認

## PHASE 9: ASSETS
- [ ] アイコン生成（SnapAI）+ グラデーション背景追加
- [ ] スクショ EN 3枚（Pencil + 1290×2796）
- [ ] スクショ JA 3枚
- [ ] iPad 13" スクショ EN + JA（2048×2732）
- [ ] ASCアップロード
- [ ] メタデータアップロード（title/subtitle/description/keywords）
- [ ] copyright + contentRights + pricing 設定
- [ ] usesIdfa: false 設定

## PHASE 10: BUILD & UPLOAD
- [ ] fastlane gym ビルド
- [ ] asc publish appstore アップロード
- [ ] TestFlight 配布

## PHASE 11: PREFLIGHT
- [ ] GATE 1-11 全PASS

## PHASE 11.5: APP PRIVACY（STOP 3）
- [ ] ユーザーにASC手動設定依頼

## PHASE 12: SUBMIT
- [ ] GUI: IAP選択
- [ ] asc review submissions-create
- [ ] asc review items-add
- [ ] asc review submissions-submit
- [ ] WAITING_FOR_REVIEW 確認
