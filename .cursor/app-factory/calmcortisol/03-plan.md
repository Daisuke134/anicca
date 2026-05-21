# CalmCortisol — Technical Plan

## アーキテクチャ

```
CalmCortisolApp
├── App/
│   └── CalmCortisolApp.swift        # @main, RevenueCat + Mixpanel 初期化
├── Models/
│   ├── BreathingType.swift           # Box / 4-7-8 / PhysiologicalSigh enum
│   ├── BreathingSession.swift        # セッションモデル
│   └── UserProfile.swift            # ペイン種別・履歴
├── Services/
│   ├── SubscriptionManager.swift    # RevenueCat wrapper + Mixpanel連携
│   ├── NotificationService.swift    # APNs + プロアクティブスケジューリング
│   ├── SessionStore.swift           # UserDefaults に履歴保存
│   └── AnalyticsService.swift       # Mixpanel イベント送信
├── Views/
│   ├── Onboarding/
│   │   ├── WelcomeView.swift
│   │   ├── PainSelectionView.swift
│   │   ├── DemoSessionView.swift
│   │   └── NotificationPermissionView.swift
│   ├── Paywall/
│   │   └── PaywallView.swift        # RevenueCat Offerings 表示
│   ├── Main/
│   │   ├── DashboardView.swift      # コルチゾールバー + クイックスタート
│   │   └── SessionHistoryCard.swift
│   ├── Session/
│   │   ├── BreathingSessionView.swift
│   │   ├── BreathingAnimationView.swift  # 円拡縮アニメーション
│   │   └── PostSessionFeedbackView.swift
│   └── Settings/
│       └── SettingsView.swift
├── Resources/
│   ├── Localizable.strings (en)
│   ├── Localizable.strings (ja)
│   └── Assets.xcassets/
│       └── AppIcon.appiconset/
└── PrivacyInfo.xcprivacy
```

## データフロー

```
ユーザー起動
  → AppDelegate: RC.configure() + Mixpanel.initialize()
  → UserDefaults に onboardingComplete フラグ確認
    → false: OnboardingFlow
    → true: DashboardView

通知フロー:
  NotificationService → 時刻スケジュール（朝9時/昼14時/夜21時）
  → ユーザータップ → DashboardView → BreathingSessionView

購入フロー:
  PaywallView → SubscriptionManager.purchase()
  → RC.purchase() → Mixpanel.track("subscription_started")
  → isPro = true → 全機能解放
```

## Free vs Pro 差分

| 機能 | Free | Pro |
|------|------|-----|
| セッション数/日 | 3回まで | 無制限 |
| 呼吸タイプ | Box Breathing のみ | 3種類 + AI推薦 |
| 就寝前セッション | なし | あり（21時以降） |
| コルチゾールグラフ | 今日のみ | 7日間履歴 |
| 通知カスタマイズ | なし | あり |
