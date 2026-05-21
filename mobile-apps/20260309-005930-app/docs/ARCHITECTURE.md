# Architecture: LumaRed

Source: [Apple Developer: App Architecture](https://developer.apple.com/documentation/swift/swift-standard-library) — 「MVVM with SwiftUI for unidirectional data flow.」
Source: [Apple Developer: BackgroundTasks](https://developer.apple.com/documentation/backgroundtasks) — 「BGTaskScheduler for deferrable background processing.」
Source: [RevenueCat: iOS SDK](https://www.revenuecat.com/docs/getting-started/installation/ios) — 「Purchases.configure(withAPIKey:) in app entry point.」

---

## 1. Platform Requirements

| 項目 | 値 |
|------|-----|
| iOS minimum | iOS 17.0 |
| Xcode version | Xcode 16.0+ |
| Swift version | Swift 5.10+ |
| Bundle ID | com.aniccafactory.lumared |
| Deployment target | iPhone only（iPad サポートなし — Rule 24 6.9"スクショ） |

---

## 2. System Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                      App Layer (SwiftUI)                │
│  OnboardingView → PaywallView (自前, RC-UI-library禁止)   │
│  HomeView → TimerView → DashboardView → SettingsView   │
└─────────────────────────┬───────────────────────────────┘
                          │ @StateObject / @EnvironmentObject
┌─────────────────────────▼───────────────────────────────┐
│                 ViewModel Layer (MVVM)                  │
│  HomeViewModel  TimerViewModel  DashboardViewModel      │
│  OnboardingViewModel  SettingsViewModel                 │
└──────┬──────────────────┬──────────────────┬────────────┘
       │                  │                  │
┌──────▼──────┐  ┌────────▼───────┐  ┌──────▼──────────┐
│  Session    │  │  Subscription  │  │  Notification   │
│  Service   │  │  Service       │  │  Service        │
│(UserDefaults)│  │ (RevenueCat)  │  │(UserNotifications)│
└──────┬──────┘  └────────┬───────┘  └──────┬──────────┘
       │                  │                  │
┌──────▼──────────────────▼──────────────────▼──────────┐
│                    Data Layer                         │
│  UserDefaults (sessions, streak, settings)            │
│  ProtocolLibrary (静的コンテンツ — AI不使用, Rule 21)   │
│  BackgroundTaskScheduler (タイマー継続)                │
└───────────────────────────────────────────────────────┘
```

---

## 3. Directory Structure

```
LumaRed/
├── LumaRedApp.swift              # @main — RevenueCat.configure, BGTask登録
├── ContentView.swift             # Tab NavigationView
├── Models/
│   ├── Protocol.swift            # struct Protocol: Codable, Identifiable
│   ├── Session.swift             # struct Session: Codable, Identifiable
│   └── ProtocolLibrary.swift     # static let protocols: [Protocol] — 静的コンテンツ
├── Services/
│   ├── SessionService.swift      # protocol SessionServiceProtocol + UserDefaults実装
│   ├── SubscriptionService.swift # protocol SubscriptionServiceProtocol + RevenueCat実装
│   └── NotificationService.swift # UNUserNotificationCenter ラッパー
├── ViewModels/
│   ├── OnboardingViewModel.swift
│   ├── HomeViewModel.swift
│   ├── TimerViewModel.swift
│   └── DashboardViewModel.swift
├── Views/
│   ├── Onboarding/
│   │   ├── OnboardingView.swift      # ウェルカム → 特徴 → 通知許可 → Paywall
│   │   └── PaywallView.swift         # 自前SwiftUI（RC-UI-library禁止 — Rule 20）
│   ├── Home/
│   │   ├── HomeView.swift            # プロトコル一覧 (F-001)
│   │   └── ProtocolCardView.swift
│   ├── Timer/
│   │   └── TimerView.swift           # カウントダウン (F-002)
│   ├── Dashboard/
│   │   └── DashboardView.swift       # Charts (F-006)
│   └── Settings/
│       └── SettingsView.swift        # 設定・Upgrade
├── Resources/
│   ├── Localizable.xcstrings         # en-US + ja
│   └── PrivacyInfo.xcprivacy
├── Config/
│   └── LumaRed.xcconfig              # RC_API_KEY (ハードコード禁止)
└── Tests/
    └── LumaRedTests/
        ├── SessionServiceTests.swift
        ├── SubscriptionServiceTests.swift
        └── TimerViewModelTests.swift
```

---

## 4. Dependencies

Source: [RevenueCat iOS Installation](https://www.revenuecat.com/docs/getting-started/installation/ios) — 「Add RevenueCat via Swift Package Manager.」

| Package | Version | Purpose | SPM URL |
|---------|---------|---------|---------|
| RevenueCat | ≥ 5.0 | サブスクリプション管理 | https://github.com/RevenueCat/purchases-ios |

**🔴 禁止パッケージ:**

| 禁止 | 理由 |
|------|------|
| RC-UI-library | Rule 20 — 自前PaywallView必須 |
| tracking-SDK | Rule 17 — アナリティクスSDK禁止 |
| third-party-analytics | Rule 17 — アナリティクスSDK禁止 |
| third-party-AI-API | Rule 21 — AI API禁止 |
| third-party-AI-API | Rule 21 — AI API禁止 |
| Google Generative AI | Rule 21 — AI API禁止 |
| AppTrackingTransparency | Rule 20b — ATT禁止 |

Feature IDs → Dependencies:

| Feature ID | 依存 |
|-----------|------|
| F-001 (プロトコルライブラリ) | なし（静的コンテンツ） |
| F-002 (タイマー) | BackgroundTasks (Apple標準) |
| F-003 (セッションログ) | UserDefaults (Apple標準) |
| F-004 (ペイウォール) | RevenueCat SDK |
| F-005 (通知) | UserNotifications (Apple標準) |
| F-006 (ダッシュボード) | Charts (Apple標準 iOS 16+) |

---

## 5. Data Models

```swift
// Protocol.swift
struct LightProtocol: Codable, Identifiable {
    let id: String                  // e.g., "face"
    let name: String                // e.g., "Face & Skin"
    let bodyPart: BodyPart
    let wavelength: String          // e.g., "630–660nm (red)"
    let distance: String            // e.g., "6–12 inches"
    let duration: Int               // seconds
    let frequency: String           // e.g., "Daily"
    let evidenceSummary: String
    let isPremium: Bool             // false = Free tier
}

enum BodyPart: String, Codable, CaseIterable {
    case face = "face"
    case joint = "joint"
    case wound = "wound"
    case back = "back"
    case fullBody = "fullBody"
}

// Session.swift
struct Session: Codable, Identifiable {
    let id: UUID
    let date: Date
    let protocolId: String          // LightProtocol.id
    let durationCompleted: Int      // seconds actually completed
    let bodyPart: BodyPart
}

// UserDefaults Keys → §7 Storage
```

---

## 6. Services

### SessionService (protocol + DI)

```swift
protocol SessionServiceProtocol {
    func save(session: Session)
    func fetchAll() -> [Session]       // Premium: all, Free: last 7 days
    func currentStreak() -> Int
    func totalDuration() -> Int        // seconds
}

class SessionService: SessionServiceProtocol {
    // UserDefaults実装。テスト時はMockSessionServiceに差し替え可能
}
```

### SubscriptionService (protocol + DI)

```swift
protocol SubscriptionServiceProtocol {
    var isPremium: Bool { get }
    func purchase(package: Package) async throws
    func restorePurchases() async throws
    func checkEntitlement() async
}

class SubscriptionService: SubscriptionServiceProtocol {
    // RevenueCat Purchases.shared を使用
    // Purchases.shared.purchase(package:) — Rule 20
}
```

### NotificationService

```swift
class NotificationService {
    func requestPermission() async -> Bool
    func scheduleSessionComplete(after seconds: Int)
    func scheduleReminder(at hour: Int, minute: Int)
    func cancelAll()
}
```

---

## 7. Storage

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `lr_sessions` | Data (JSON) | [] | セッションログ配列 |
| `lr_onboarding_complete` | Bool | false | オンボーディング完了フラグ |
| `lr_notification_enabled` | Bool | false | 通知設定 |
| `lr_reminder_hour` | Int | 9 | リマインダー時刻（時） |
| `lr_reminder_minute` | Int | 0 | リマインダー時刻（分） |
| `lr_last_session_date` | Date? | nil | 連続日数計算用 |

---

## 8. AI Integration

**🔴 Rule 21 適用: AI API / AI モデル / 外部 AI サービス完全禁止。**

| 禁止 | 代替 |
|------|------|
| third-party-AI-API | 静的キュレーションコンテンツ（ProtocolLibrary.swift） |
| third-party-AI-API | 静的コンテンツ |
| Google Generative AI | 静的コンテンツ |
| Apple on-device-AI-framework（iOS 26+） | iOS 26+ = ユーザーベース皆無。静的コンテンツ |

プロトコルコンテンツはすべてアプリバンドルに静的に含める。月収$29 vs API費用$300+ のためAPIコスト発生禁止。

---

## 9. Networking

| 種類 | 詳細 |
|------|------|
| 外部API | なし（完全自己完結） |
| RevenueCat | SDK経由。ユーザーのサブスク状態確認のみ |
| App Store | StoreKit 2 経由（RevenueCat SDK 内部） |

---

## 10. Notifications

Source: [Apple Developer: UNUserNotificationCenter](https://developer.apple.com/documentation/usernotifications/unusernotificationcenter) — 「Use UNCalendarNotificationTrigger for daily reminders.」

| タイプ | トリガー | 内容 |
|--------|---------|------|
| セッション完了通知 | タイマー終了時（UNTimeIntervalNotificationTrigger） | "Session complete! Great work." |
| 日次リマインダー | 毎日 9:00（UNCalendarNotificationTrigger） | "Time for your red light session." |

BackgroundTask（BGProcessingTaskRequest）を使ってバックグラウンドでタイマー継続。アプリがkillされた場合は通知でユーザーに知らせる。

---

## 11. Privacy

| 項目 | 値 |
|------|-----|
| PrivacyInfo.xcprivacy | 必須（ITMS-91053 回避） |
| NSPrivacyAccessedAPICategoryUserDefaults | CA92.1（セッションログ保存） |
| ATT | **不使用（Rule 20b）** |
| NSUserTrackingUsageDescription | **追加禁止（Rule 20b）** |
| データ送信 | なし（サーバー未使用） |
| HealthKit | **不使用（MVP Out of Scope）** |

---

## 12. Error Handling

| エラー種別 | ハンドリング | ユーザー向けメッセージ |
|-----------|------------|----------------------|
| RevenueCat 購入失敗 | Purchases.ErrorCode 判別。キャンセルはサイレント | "Purchase failed. Please try again." |
| RevenueCat ネットワークエラー | 3回リトライ後 UI に表示 | "Network error. Check connection." |
| UserDefaults 保存失敗 | ログ警告、クラッシュさせない | — |
| BackgroundTask 登録失敗 | Info.plist に BGTaskSchedulerPermittedIdentifiers 追加 | — |
| 通知権限拒否 | UserDefaults に状態保存。設定画面から誘導 | "Enable notifications in Settings." |
