# BreathReset Technical Plan

## アーキテクチャ（SwiftUI MVC）

```
BreathResetApp
├── App/
│   ├── BreathResetApp.swift          ← @main エントリーポイント
│   └── ContentView.swift              ← タブビュー分岐
├── Models/
│   ├── BreathingTechnique.swift       ← 呼吸法定義（6種類）
│   ├── BreathingSession.swift         ← セッション記録
│   └── UserStats.swift                ← ストリーク・統計
├── Services/
│   ├── SubscriptionManager.swift      ← RevenueCat
│   ├── NotificationService.swift      ← APNs / 3回通知
│   ├── SessionStore.swift             ← UserDefaults 永続化
│   └── MixpanelService.swift          ← 分析
├── Views/
│   ├── Onboarding/
│   │   ├── WelcomeView.swift
│   │   ├── ProblemView.swift
│   │   └── SolutionView.swift
│   ├── Home/
│   │   └── HomeView.swift
│   ├── Session/
│   │   ├── SessionView.swift          ← 呼吸アニメーション
│   │   ├── BreathingCircleView.swift  ← 円アニメーション
│   │   └── TechniquePickerView.swift
│   ├── Stats/
│   │   └── StatsView.swift
│   ├── Paywall/
│   │   └── PaywallView.swift          ← RevenueCat UI
│   └── Settings/
│       └── SettingsView.swift
├── Resources/
│   ├── Localizable.strings (en + ja)
│   └── Assets.xcassets/AppIcon.appiconset/
└── BreathResetUITests/
    └── ScreenshotTests.swift
```

## RevenueCat 設計

| 項目 | 値 |
|------|-----|
| Monthly Product ID | com.anicca.breathreset.premium.monthly |
| Annual Product ID | com.anicca.breathreset.premium.yearly |
| Entitlement | premium |
| Offering ID | default |

## 通知設計

| 時刻 | タイトル(EN) | タイトル(JA) |
|------|------------|------------|
| 9:00 AM | "Morning Reset 🌬️" | "朝のリセット 🌬️" |
| 2:00 PM | "Afternoon Brain Boost" | "午後の脳ブースト" |
| 8:00 PM | "Evening Wind Down" | "夜のリラックス" |

## BreathingTechnique モデル

```swift
struct BreathingTechnique: Identifiable {
    let id: String
    let nameKey: String          // Localizable.strings キー
    let inhale: Double           // 秒
    let hold1: Double            // 秒
    let exhale: Double           // 秒
    let hold2: Double            // 秒
    let cycles: Int              // 繰り返し回数
    let durationMinutes: Int     // 合計時間
    let isPremium: Bool          // Free/Premium
    let scienceBasis: String     // 科学的根拠（表示用）
}
```

## API / RevenueCat 設計

- RevenueCat SDK v4（Swift Package Manager）
- Offerings: `Packages.current` で月額・年額を取得
- Entitlements: `"premium"` entitlement でロック制御
- Mixpanel: `paywall_viewed`（offering_id付き）送信必須

## Mixpanel イベント

| イベント | プロパティ |
|---------|-----------|
| onboarding_started | - |
| onboarding_completed | - |
| paywall_viewed | offering_id |
| session_started | technique_id, is_premium |
| session_completed | technique_id, duration_seconds |
| streak_achieved | days |
