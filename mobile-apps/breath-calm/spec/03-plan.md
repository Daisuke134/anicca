# BreathCalm — plan.md (技術設計)

Generated: 2026-02-24

---

## アーキテクチャ

**SwiftUI MVC + RevenueCat + Mixpanel**

```
BreathCalmApp (App entry point)
├── OnboardingFlow
│   ├── WelcomeView
│   ├── AnxietyLevelView
│   └── NotificationPermissionView
├── MainTabView
│   ├── HomeView
│   │   ├── SessionCardView (session type cards)
│   │   └── SOSButton
│   ├── HistoryView
│   │   └── SessionRowView
│   └── SettingsView
├── SessionFlow
│   ├── PreSessionMoodView
│   ├── BreathingSessionView (animation + timer)
│   └── PostSessionMoodView (before/after comparison)
├── PaywallView (RevenueCat + accessibilityIdentifiers)
└── Services
    ├── SubscriptionManager (RevenueCat)
    ├── SessionManager (session data, streaks)
    ├── AudioManager (AVAudioEngine + binaural beats)
    ├── MixpanelService (analytics)
    └── NotificationManager (UserNotifications)
```

---

## ファイル構成

```
BreathCalmApp/
├── BreathCalmApp.swift          # @main エントリーポイント
├── ContentView.swift            # Root view (onboarding vs main)
├── Info.plist
├── PrivacyInfo.xcprivacy        # 必須: NSPrivacyAccessedAPICategoryUserDefaults
├── Assets.xcassets/
│   └── AppIcon.appiconset/
│       └── icon.png             # 1024×1024
├── Localizable.strings (Base/en)
├── Localizable.strings (ja)
│
├── Onboarding/
│   ├── WelcomeView.swift
│   ├── AnxietyLevelView.swift
│   └── NotificationPermissionView.swift
│
├── Main/
│   ├── MainTabView.swift
│   ├── HomeView.swift
│   ├── HistoryView.swift
│   └── SettingsView.swift
│
├── Session/
│   ├── PreSessionMoodView.swift
│   ├── BreathingSessionView.swift
│   ├── PostSessionMoodView.swift
│   └── BreathingAnimation.swift  # 呼吸アニメーション
│
├── Paywall/
│   └── PaywallView.swift
│
├── Models/
│   ├── BreathingSession.swift    # セッションデータモデル
│   ├── SessionType.swift         # 4-7-8, Box, Coherent, SOS, Walking
│   └── MoodEntry.swift
│
├── Services/
│   ├── SubscriptionManager.swift
│   ├── SessionManager.swift
│   ├── AudioManager.swift
│   ├── MixpanelService.swift
│   └── NotificationManager.swift
│
└── Resources/
    └── Audio/                    # 呼吸ガイド音声 + バイノーラルビーツ
        ├── binaural_alpha.mp3
        ├── binaural_theta.mp3
        └── guide_478.mp3
```

---

## 主要データモデル

### BreathingSession

```swift
struct BreathingSession: Codable, Identifiable {
    let id: UUID
    let date: Date
    let type: SessionType
    let durationSeconds: Int
    let preMoodScore: Int      // 0-10
    let postMoodScore: Int?    // 0-10 (nil = not completed)
}
```

### SessionType

```swift
enum SessionType: String, CaseIterable, Codable {
    case breathing478 = "4-7-8 Breathing"
    case box = "Box Breathing"
    case coherent = "Coherent Breathing"
    case sos = "SOS Relief"
    case japaneseWalking = "Japanese Walking"

    var durationSeconds: Int {
        switch self {
        case .sos: return 360      // 6分
        case .breathing478: return 240  // 4分
        case .box: return 300      // 5分
        case .coherent: return 360
        case .japaneseWalking: return 600  // 10分
        }
    }

    var isPro: Bool {
        switch self {
        case .breathing478: return false  // Freeでも使える
        default: return true
        }
    }
}
```

---

## Audio設計

| 種類 | 実装 |
|------|------|
| バイノーラルビーツ | AVAudioEngine で L/R チャンネルに異なる周波数を出力 |
| 呼吸ガイド音声 | AVAudioPlayer でガイドナレーション再生 |
| 呼吸タイミング | Timer + AnimationTimeline で同期 |

**バイノーラル周波数設計:**
- Alpha (8-14Hz): リラックス用
- Theta (4-8Hz): 深いリラックス / 瞑想用
- Free版: 基本トーンのみ (binaural OFF)

---

## Mixpanel イベント設計

| イベント | プロパティ | タイミング |
|---------|-----------|-----------|
| `onboarding_started` | - | WelcomeView表示時 |
| `onboarding_paywall_viewed` | `offering_id` | Paywall表示時 |
| `session_started` | `session_type`, `is_pro` | セッション開始時 |
| `session_completed` | `session_type`, `pre_mood`, `post_mood`, `duration` | セッション完了時 |
| `sos_triggered` | - | SOSボタンタップ時 |
| `paywall_viewed` | `offering_id` | Paywall表示時（追加） |

---

## RevenueCat設計

- SDK: `RevenueCat/RevenueCat` via SPM
- APIKey: `.env` の `REVENUECAT_IOS_KEY`
- Entitlement: `premium`
- Free制限: SessionManager で `SubscriptionManager.isSubscribed` チェック

---

## 通知設計

| 通知 | タイミング | コンテンツ |
|------|----------|----------|
| 毎日リマインダー | ユーザー設定時刻 (デフォルト20:00) | 「今日の呼吸セッションを始めましょう」 |
| ストリーク維持 | 24時間セッションなし | 「昨日はお休みしましたね。今日の呼吸で再スタート」 |
