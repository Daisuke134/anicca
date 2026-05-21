# Architecture: Zone2Daily

Source: [Apple Developer — SwiftUI App Architecture](https://developer.apple.com/documentation/swiftui) — 「MVVM with @Observable is the recommended pattern for SwiftUI iOS 17+.」
Source: [Swift Evolution SE-0395 — @Observable](https://github.com/apple/swift-evolution/blob/main/proposals/0395-observability.md) — 「@Observable replaces ObservableObject with zero boilerplate.」
Source: [SwiftData WWDC 2023](https://developer.apple.com/videos/play/wwdc2023/10187/) — 「SwiftData is the modern replacement for CoreData on iOS 17+.」

---

## 1. Platform Requirements

| 項目 | 値 |
|------|-----|
| iOS Minimum | 17.0 |
| Xcode | 16.0+ |
| Swift | 5.10+ |
| Deployment Target | iPhone only (iPad auto-scale) |
| Bundle ID | `com.aniccafactory.zone2daily` |
| Architectures | arm64 (device + simulator) |

---

## 2. System Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     App Layer (SwiftUI)                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Onboarding  │  │  Dashboard   │  │    Workout     │  │
│  │    Views    │  │    Views     │  │    Views       │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘  │
│         │                │                  │            │
│  ┌──────▼──────┐  ┌──────▼───────┐  ┌───────▼────────┐  │
│  │ Onboarding  │  │  Dashboard   │  │    Workout     │  │
│  │  ViewModel  │  │   ViewModel  │  │   ViewModel    │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘  │
├─────────┼────────────────┼──────────────────┼────────────┤
│         │     Service Layer                 │            │
│  ┌──────▼──────────────────────────────────▼────────┐   │
│  │  SubscriptionService (RevenueCat)                 │   │
│  │  NotificationService (UNUserNotificationCenter)   │   │
│  │  Zone2Calculator (Pure Function — Maffetone)      │   │
│  └──────────────────────────┬────────────────────────┘   │
├─────────────────────────────┼──────────────────────────── │
│                Data Layer   │                              │
│  ┌──────────────────────────▼────────────────────────┐   │
│  │  SwiftData (WorkoutSession, UserProfile)           │   │
│  │  UserDefaults (onboarding flag, settings)          │   │
│  └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Directory Structure

```
Zone2Daily/
├── App/
│   ├── Zone2DailyApp.swift          # @main, RevenueCat configure()
│   └── AppState.swift               # @Observable global state
├── Models/
│   ├── WorkoutSession.swift         # SwiftData @Model
│   └── UserProfile.swift            # SwiftData @Model (age, weeklyGoal)
├── Services/
│   ├── SubscriptionServiceProtocol.swift   # Protocol for DI
│   ├── SubscriptionService.swift           # RevenueCat implementation
│   ├── NotificationService.swift           # UNUserNotificationCenter
│   └── Zone2Calculator.swift               # Pure function: 180 - age
├── ViewModels/
│   ├── OnboardingViewModel.swift
│   ├── WorkoutViewModel.swift
│   └── DashboardViewModel.swift
├── Views/
│   ├── Onboarding/
│   │   ├── OnboardingContainerView.swift
│   │   ├── AgeInputView.swift
│   │   ├── Zone2ExplainerView.swift
│   │   ├── NotificationPermissionView.swift
│   │   └── PaywallView.swift            # Rule 20: 自前 SwiftUI
│   ├── Dashboard/
│   │   ├── DashboardView.swift
│   │   └── WeeklyProgressView.swift
│   ├── Workout/
│   │   ├── WorkoutTimerView.swift
│   │   └── WorkoutLogView.swift
│   └── Settings/
│       └── SettingsView.swift
├── DesignSystem/
│   ├── Colors.swift                 # Brand color tokens
│   ├── Typography.swift             # Font scale
│   └── Spacing.swift                # 4pt grid
├── Resources/
│   ├── Localizable.xcstrings        # en-US + ja
│   ├── Assets.xcassets
│   └── PrivacyInfo.xcprivacy        # NSPrivacyAccessedAPICategoryUserDefaults CA92.1
└── Zone2DailyTests/
    └── (Unit + Integration tests)
```

---

## 4. Dependencies

Source: [RevenueCat iOS SDK](https://docs.revenuecat.com/docs/ios) — 「The standard SDK for managing subscriptions on iOS.」
Source: [Apple App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/#payments) — 「Third-party subscription management via RevenueCat is approved.」

| Package | Version | URL | Purpose |
|---------|---------|-----|---------|
| **RevenueCat** | 5.x (latest) | https://github.com/RevenueCat/purchases-ios | Subscription management |

**🔴 禁止パッケージ:**

| 禁止パッケージ | 理由 |
|-------------|------|
| RC-UI-Framework (RevenueCat UI 拡張) | Rule 20: 自前 PaywallView 必須 |
| Third-party tracking SDKs (Rule 17) | Tracking SDK 禁止 — Greenlight CRITICAL |
| AI SDK 全般 (Rule 21) | 月収 $29 vs API コスト $300+ |
| On-device LLM (iOS 26+ only) | Rule 21: ユーザーベース皆無 |

---

## 5. Data Models

### WorkoutSession (SwiftData @Model)

```swift
// File: Models/WorkoutSession.swift
import SwiftData
import Foundation

@Model
final class WorkoutSession {
    var id: UUID
    var date: Date
    var durationSeconds: Int          // Total workout duration
    var zone2Seconds: Int             // Time spent in Zone 2
    var targetHR: Int                 // Calculated from age at time of workout
    var notes: String?

    init(date: Date = .now, durationSeconds: Int, zone2Seconds: Int, targetHR: Int) {
        self.id = UUID()
        self.date = date
        self.durationSeconds = durationSeconds
        self.zone2Seconds = zone2Seconds
        self.targetHR = targetHR
    }

    // Derived
    var zone2Minutes: Double { Double(zone2Seconds) / 60.0 }
    var zone2Percentage: Double {
        guard durationSeconds > 0 else { return 0 }
        return Double(zone2Seconds) / Double(durationSeconds) * 100.0
    }
}
```

### UserProfile (SwiftData @Model)

```swift
// File: Models/UserProfile.swift
import SwiftData

@Model
final class UserProfile {
    var age: Int
    var weeklyGoalMinutes: Int        // Default: 150
    var createdAt: Date

    init(age: Int, weeklyGoalMinutes: Int = 150) {
        self.age = age
        self.weeklyGoalMinutes = weeklyGoalMinutes
        self.createdAt = .now
    }

    // Maffetone Formula: F-001
    var zone2MaxHR: Int { 180 - age }
    var zone2MinHR: Int { zone2MaxHR - 10 }  // ±10 bpm range
}
```

Source: [Maffetone — 180 Formula](https://philmaffetone.com/180-formula/) — 「Maximum Aerobic Function HR = 180 - age.」

---

## 6. Services

### Zone2Calculator

```swift
// File: Services/Zone2Calculator.swift
enum Zone2Calculator {
    // F-001: Maffetone Method
    static func zone2MaxHR(age: Int) -> Int { 180 - age }
    static func zone2MinHR(age: Int) -> Int { zone2MaxHR(age: age) - 10 }
    static func zone2Range(age: Int) -> ClosedRange<Int> {
        zone2MinHR(age: age)...zone2MaxHR(age: age)
    }
}
```

### SubscriptionServiceProtocol

```swift
// File: Services/SubscriptionServiceProtocol.swift
protocol SubscriptionServiceProtocol {
    var isPremium: Bool { get }
    func fetchOfferings() async throws -> [Package]
    func purchase(package: Package) async throws -> Bool
    func restorePurchases() async throws
}
```

### SubscriptionService (RevenueCat)

```swift
// File: Services/SubscriptionService.swift
import RevenueCat  // Rule 20: SDK only, UI extension forbidden

@Observable
final class SubscriptionService: SubscriptionServiceProtocol {
    var isPremium: Bool = false

    func configure(apiKey: String) {
        Purchases.configure(withAPIKey: apiKey)
    }

    func fetchOfferings() async throws -> [Package] {
        let offerings = try await Purchases.shared.offerings()
        return offerings.current?.availablePackages ?? []
    }

    func purchase(package: Package) async throws -> Bool {
        let result = try await Purchases.shared.purchase(package: package)
        return !result.userCancelled
    }

    func restorePurchases() async throws {
        _ = try await Purchases.shared.restorePurchases()
    }
}
```

### NotificationService

```swift
// File: Services/NotificationService.swift
import UserNotifications

actor NotificationService {
    func requestPermission() async -> Bool {
        let center = UNUserNotificationCenter.current()
        let status = try? await center.requestAuthorization(options: [.alert, .sound, .badge])
        return status ?? false
    }

    func scheduleDailyReminder(hour: Int = 8, minute: Int = 0) async {
        let content = UNMutableNotificationContent()
        content.title = "Zone 2 Time!"
        content.body = "Ready for your Zone 2 session today?"
        content.sound = .default

        var comps = DateComponents()
        comps.hour = hour
        comps.minute = minute
        let trigger = UNCalendarNotificationTrigger(dateMatching: comps, repeats: true)
        let request = UNNotificationRequest(identifier: "zone2daily.morning", content: content, trigger: trigger)
        try? await UNUserNotificationCenter.current().add(request)
    }
}
```

---

## 7. Storage

### UserDefaults キー

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `hasCompletedOnboarding` | Bool | false | オンボーディング完了フラグ |
| `notificationsEnabled` | Bool | false | 通知許可状態 |
| `notificationHour` | Int | 8 | 通知時刻（時） |
| `notificationMinute` | Int | 0 | 通知時刻（分） |

### SwiftData

| Store | Models | Purpose |
|-------|--------|---------|
| `zone2daily.store` | WorkoutSession, UserProfile | ローカル永続化（iCloud同期なし） |

Source: [Apple SwiftData Docs](https://developer.apple.com/documentation/swiftdata) — 「SwiftData automatically creates the persistent store at the app's default location.」

---

## 8. AI Integration

**🔴 Rule 21: AI API / AI モデル / 外部 AI サービス完全禁止**

| 禁止 | 理由 |
|------|------|
| AI completion API | 月収 $29 vs API コスト $300+ |
| Anthropic Claude | 同上 |
| Google Gemini | 同上 |
| On-device LLM (iOS 26+) | ユーザーベース皆無 |
| On-device ML (CoreML) | 必要性なし |

**代替:** Zone 2 計算は純粋な数式（180 − 年齢）のみ。CoreML 不要。

---

## 9. Networking

**外部 API 通信なし** — アプリは完全ローカル動作。

| 通信 | 対象 | 方式 |
|------|------|------|
| RevenueCat | 課金検証のみ | RevenueCat SDK 内部（HTTPS） |
| その他 | なし | — |

---

## 10. Notifications

| 通知種別 | トリガー | コンテンツ |
|---------|---------|----------|
| 毎朝リマインダー | 毎日 8:00（ユーザー変更可） | "Zone 2 Time! / Ready for your Zone 2 session?" |

- `UNCalendarNotificationTrigger` with `repeats: true`
- Identifier: `zone2daily.morning`（上書き登録で重複防止）

Source: [Apple UNUserNotificationCenter](https://developer.apple.com/documentation/usernotifications/unusernotificationcenter) — 「Use UNCalendarNotificationTrigger for daily recurring notifications.」

---

## 11. Privacy

| 項目 | 設定 |
|------|------|
| PrivacyInfo.xcprivacy | 必須（ITMS-91053 対策） |
| NSPrivacyAccessedAPITypes | UserDefaults: CA92.1 |
| ATT | **不使用** — Rule 20b |
| Tracking/Event SDKs | **禁止** — Rule 17 |
| Server-side collection | なし |
| Third-party data sharing | なし |

Source: [Apple Privacy Manifest Required Reasons](https://developer.apple.com/documentation/bundleresources/privacy_manifest_files/describing_use_of_required_reason_api) — 「NSPrivacyAccessedAPICategoryUserDefaults must list CA92.1 for app functionality.」

---

## 12. Error Handling

| エラー種別 | 発生箇所 | ハンドリング | ユーザーメッセージ |
|-----------|---------|------------|----------------|
| RevenueCat purchase failure | SubscriptionService.purchase() | catch → isPremium = false | "Purchase failed. Please try again." |
| RevenueCat network error | fetchOfferings() | catch → fallback to empty | "Could not load offerings." |
| Notification permission denied | NotificationService | Bool false → show settings link | "Enable notifications in Settings" |
| SwiftData save failure | WorkoutViewModel | catch → log + alert | "Could not save workout." |
| Invalid age input (<10, >120) | AgeInputView | Disable CTA | — (input validation) |
