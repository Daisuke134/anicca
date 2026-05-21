# Architecture: VagusReset

Source: [Apple SwiftUI Documentation](https://developer.apple.com/documentation/swiftui) — 「SwiftUI provides views, controls, and layout structures for declaring your app's user interface」
Source: [Swift MVVM Architecture Guide](https://www.kodeco.com/34699757-swiftui-mvvm-get-started) — 「MVVM separates business logic from UI」
Source: [Apple App Review Guidelines §5.1](https://developer.apple.com/app-store/review/guidelines/#privacy) — 「Apps must request only necessary permissions」

---

## 1. Platform Requirements

| 項目 | 値 |
|------|-----|
| iOS Minimum | iOS 17.0 |
| Xcode Version | Xcode 16.0+ |
| Swift Version | Swift 5.10+ |
| SwiftUI | 5.0+ |
| Target Device | iPhone（Universal対応なし — iPad は自動スケール） |
| Architecture | arm64 |
| bundle_id | com.aniccafactory.vagusreset |

---

## 2. System Architecture Diagram

```
┌────────────────────────────────────────┐
│              App Layer                 │
│  VagusResetApp.swift (@main)           │
│  ContentView.swift (RootView)          │
└──────────────┬─────────────────────────┘
               │ ObservableObject / @StateObject
┌──────────────▼─────────────────────────┐
│           ViewModel Layer              │
│  OnboardingViewModel  HomeViewModel    │
│  SessionViewModel     SettingsViewModel│
└──────────────┬─────────────────────────┘
               │ Protocol DI
┌──────────────▼─────────────────────────┐
│           Service Layer                │
│  SubscriptionService (Protocol + DI)   │
│  StreakService                         │
│  NotificationService                   │
│  ExerciseRepository                    │
└──────────────┬─────────────────────────┘
               │
┌──────────────▼─────────────────────────┐
│            Data Layer                  │
│  UserDefaults  ExerciseData.json       │
│  RevenueCat SDK  Keychain（RC SK Key） │
└────────────────────────────────────────┘
```

---

## 3. Directory Structure

```
VagusReset/
├── App/
│   ├── VagusResetApp.swift        # @main, Purchases.configure(withAPIKey:)
│   └── ContentView.swift          # RootView: onboarding state router
├── Config/
│   └── VagusReset.xcconfig        # RC_PUBLIC_KEY (not hardcoded)
├── Models/
│   ├── Exercise.swift             # Codable struct: id, title, duration, category, isPremium
│   ├── ExerciseSession.swift      # Codable struct: exerciseId, date, durationSeconds
│   └── ExerciseData.json          # 20+ exercises static content
├── ViewModels/
│   ├── OnboardingViewModel.swift  # @Published currentStep, isOnboardingComplete
│   ├── HomeViewModel.swift        # @Published exercises, streak, isPremium
│   ├── SessionViewModel.swift     # @Published timeRemaining, isRunning, isComplete
│   └── SettingsViewModel.swift    # @Published notificationTime, isPremium
├── Views/
│   ├── Onboarding/
│   │   ├── OnboardingView.swift
│   │   ├── OnboardingStep1View.swift  # 問題提示
│   │   ├── OnboardingStep2View.swift  # 解決策
│   │   └── PaywallView.swift          # Custom SwiftUI (RC-UI-package 禁止 — Rule 20)
│   ├── Home/
│   │   ├── HomeView.swift
│   │   └── ExerciseCardView.swift
│   ├── Session/
│   │   ├── SessionView.swift
│   │   └── TimerView.swift
│   └── Settings/
│       ├── SettingsView.swift
│       └── ProgressCalendarView.swift  # 有料機能
├── Services/
│   ├── SubscriptionServiceProtocol.swift  # Protocol (testable DI)
│   ├── SubscriptionService.swift          # Real RevenueCat implementation
│   ├── StreakService.swift                # UserDefaults wrapper
│   └── NotificationService.swift         # UNUserNotificationCenter wrapper
├── Resources/
│   └── PrivacyInfo.xcprivacy             # NSPrivacyAccessedAPICategoryUserDefaults CA92.1
└── Tests/
    └── VagusResetTests/
        ├── SubscriptionServiceTests.swift
        ├── StreakServiceTests.swift
        └── SessionViewModelTests.swift
```

---

## 4. Dependencies

| Package | Version | Purpose | Source |
|---------|---------|---------|--------|
| **RevenueCat** | 4.x+ | サブスク管理（購入・復元・Premium判定） | [RevenueCat SPM](https://github.com/RevenueCat/purchases-ios) |

**🔴 禁止（Rule 違反）:**

| 禁止パッケージ | 理由 |
|-------------|------|
| RC-UI-package | Rule 20: 自前 PaywallView 必須 |
| `tracking SDK 全般`（Rule 17） | Rule 17: Greenlight CRITICAL = リジェクト |
| 外部 LLM API SDK 全般（Rule 21） | Rule 21: AI API コスト禁止 |
| `AppTrackingTransparency` | Rule 20b: ATT 禁止 |

**SPM 設定:**
```
URL: https://github.com/RevenueCat/purchases-ios
Package: RevenueCat (NOT RC-UI-package)
Version: Up to Next Major 4.0.0
```

---

## 5. Data Models

```swift
// Models/Exercise.swift
struct Exercise: Codable, Identifiable {
    let id: String          // "humming-01"
    let title: String       // "Humming Breath"
    let titleJa: String     // "ハミング呼吸"
    let category: String    // "humming" | "gargling" | "cold" | "diaphragm" | "laughter"
    let durationSeconds: Int  // 60, 120, etc.
    let description: String
    let descriptionJa: String
    let isPremium: Bool     // false: 5 free exercises
    let iconName: String    // SF Symbol name
    let order: Int          // display order
}

// Models/ExerciseSession.swift
struct ExerciseSession: Codable {
    let id: UUID
    let exerciseId: String
    let date: Date          // stored in UserDefaults
    let durationSeconds: Int
    let isCompleted: Bool
}
```

---

## 6. Services

### SubscriptionServiceProtocol
```swift
protocol SubscriptionServiceProtocol: ObservableObject {
    var isPremium: Bool { get }
    func fetchOfferings() async throws -> Offerings
    func purchase(package: Package) async throws -> PurchaseResultData
    func restorePurchases() async throws -> CustomerInfo
}
```
**実装:** `SubscriptionService` — RevenueCat `Purchases.shared` を直接呼ぶ
**テスト用:** `MockSubscriptionService` — Tests/ フォルダのみ（本番コードに混入禁止）

### StreakService
```swift
class StreakService {
    func recordSessionCompletion(date: Date)
    func getCurrentStreak() -> Int
    func getLastSessionDate() -> Date?
    func getCompletedDates() -> [Date]  // for calendar view
}
```
**Storage:** UserDefaults (`vagusreset.streak.current`, `vagusreset.streak.dates`)

### NotificationService
```swift
class NotificationService {
    func requestPermission() async -> Bool
    func scheduleDaily(at time: DateComponents)
    func cancelAll()
}
```

### ExerciseRepository
```swift
class ExerciseRepository {
    func loadAll() -> [Exercise]        // from ExerciseData.json
    func loadFree() -> [Exercise]       // isPremium == false (5 items)
    func loadPremium() -> [Exercise]    // isPremium == true
}
```

---

## 7. Storage

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `vagusreset.onboarding.complete` | Bool | false | オンボーディング完了フラグ |
| `vagusreset.streak.current` | Int | 0 | 現在の連続日数 |
| `vagusreset.streak.lastDate` | String (ISO8601) | nil | 最終セッション日 |
| `vagusreset.streak.completedDates` | [String] | [] | 完了日リスト（ISO8601） |
| `vagusreset.notification.enabled` | Bool | false | 通知設定 |
| `vagusreset.notification.hour` | Int | 9 | リマインダー時間（時） |
| `vagusreset.notification.minute` | Int | 0 | リマインダー時間（分） |

---

## 8. AI Integration

**🔴 Rule 21: AI API / AI モデル / 外部 AI サービス完全禁止**

| 禁止 | 理由 |
|------|------|
| 外部 LLM API（クラウド型）| 月収 $29 vs API コスト $300+ |
| LLM クラウド API 全般 | 同上 |
| Google Generative AI | 同上 |
| Apple on-device AI (iOS 26+ only) | iOS 26+ のみ、ユーザー基盤皆無 |

**代替:** エクササイズコンテンツは `ExerciseData.json` に静的キュレーション（20+エクササイズ）。AI ゼロ、バックエンドゼロ、コストゼロ。

---

## 9. Networking

**なし。** VagusReset は完全オフライン動作。バックエンド API 不要。
- エクササイズデータ: ローカル JSON（`ExerciseData.json`）
- RevenueCat: SDK 内部で Apple StoreKit 経由（アプリ独自 API なし）

---

## 10. Notifications

| 種別 | トリガー | 内容 |
|------|---------|------|
| デイリーリマインダー | ユーザー設定時刻（デフォルト 9:00） | 「今日の迷走神経リセットの時間です 🧘」|
| ストリーク維持 | 前日セッションなし | 「ストリークが途切れそうです！2分だけ試して」|

**実装:** `UNUserNotificationCenter` + `UNCalendarNotificationTrigger`
**バックグラウンド:** タイマー（SessionViewModel）は `Timer.publish(every:)` + `RunLoop.main` で実装。バックグラウンド移行時に残り時間を保存し、フォアグラウンド復帰時に補正。

---

## 11. Privacy

| 項目 | 設定 |
|------|------|
| `PrivacyInfo.xcprivacy` | NSPrivacyAccessedAPICategoryUserDefaults: CA92.1 |
| NSPrivacyTracking | false |
| NSPrivacyCollectedDataTypes | [] （収集なし） |
| ATT | 不使用（Rule 20b） |
| カメラ・マイク | 不使用 |
| HealthKit | 不使用 |

```xml
<!-- PrivacyInfo.xcprivacy -->
<key>NSPrivacyAccessedAPITypes</key>
<array>
  <dict>
    <key>NSPrivacyAccessedAPIType</key>
    <string>NSPrivacyAccessedAPICategoryUserDefaults</string>
    <key>NSPrivacyAccessedAPITypeReasons</key>
    <array>
      <string>CA92.1</string>
    </array>
  </dict>
</array>
<key>NSPrivacyTracking</key>
<false/>
```

---

## 12. Error Handling

| Error Type | Handling | User Message |
|-----------|---------|--------------|
| RevenueCat purchase failed | `try catch` → show alert | 「購入に失敗しました。もう一度お試しください。」|
| RevenueCat restore failed | `try catch` → show alert | 「購入の復元に失敗しました。」|
| JSON decode failure | `fatalError` in DEBUG / empty array in RELEASE | （サイレント — デフォルト5種を表示） |
| Notification permission denied | Show settings deep-link | 「設定から通知を有効にしてください」|
| Timer background interruption | Store remaining time in UserDefaults | （自動補正、ユーザー通知なし） |

---

## Feature → Architecture Mapping

| Feature ID | 実装ファイル | Service | Storage |
|-----------|------------|---------|---------|
| F-001 | ExerciseRepository | — | ExerciseData.json |
| F-002 | SessionView, SessionViewModel, TimerView | — | UserDefaults (timer state) |
| F-003 | HomeView, HomeViewModel, ExerciseCardView | ExerciseRepository, SubscriptionService | — |
| F-004 | PaywallView | SubscriptionService | — |
| F-005 | HomeView (streak display) | StreakService | UserDefaults |
| F-006 | OnboardingStep2View | NotificationService | UserDefaults |
| F-007 | SettingsView, SettingsViewModel | SubscriptionService, NotificationService | UserDefaults |
| F-008 | OnboardingView, OnboardingStep1, Step2, PaywallView | OnboardingViewModel | UserDefaults |
| F-009 | ProgressCalendarView | StreakService | UserDefaults |
| F-010 | SessionView (completion animation) | — | — |
