# Architecture: LymphaFlow

Source: [Apple Developer SwiftUI](https://developer.apple.com/xcode/swiftui/) — 「Build beautiful apps with a declarative Swift syntax.」
Source: [Apple Developer App Architecture](https://developer.apple.com/documentation/swiftui/model-data) — 「MVVM pattern with ObservableObject for SwiftUI.」
Source: [RevenueCat iOS SDK](https://www.revenuecat.com/docs/getting-started/installation/ios) — 「Add as Swift Package Manager dependency.」

---

## 1. Platform Requirements

| 項目 | 値 |
|------|-----|
| iOS minimum | 17.0 |
| Xcode | 16.0+ |
| Swift | 5.9+ |
| Deployment Target | iPhone (portrait primary) |
| bundle_id | `com.aniccafactory.lymphaflow` |
| Supported Devices | iPhone (no iPad split-view required) |

---

## 2. System Architecture Diagram

```
┌──────────────────────────────────────────────────────┐
│                    App Layer (SwiftUI)                 │
│  OnboardingView  HomeView  SessionView  SettingsView  │
│  PaywallView     ProgressView  StepView               │
└─────────────────────┬────────────────────────────────┘
                       │ @StateObject / @ObservedObject
┌─────────────────────▼────────────────────────────────┐
│                 ViewModel Layer (MVVM)                 │
│  OnboardingVM   HomeVM   TimerVM   SettingsVM         │
└─────────────────────┬────────────────────────────────┘
                       │ Protocol DI
┌─────────────────────▼────────────────────────────────┐
│                   Service Layer                        │
│  SubscriptionService  SessionStore  NotificationSvc   │
│  RoutineDataService (static JSON loader)              │
└─────────┬───────────────────────┬────────────────────┘
          │                       │
┌─────────▼──────────┐  ┌────────▼──────────────────┐
│   RevenueCat SDK   │  │  UserDefaults (local)      │
│   (Purchases.*)    │  │  routines.json (bundled)   │
│   [No RC-UI lib]    │  │  UNUserNotificationCenter  │
└────────────────────┘  └───────────────────────────┘
```

---

## 3. Directory Structure

```
LymphaFlowios/
├── LymphaFlow.xcodeproj/
├── Config/
│   ├── LymphaFlow.xcconfig        # RC_API_KEY (not hardcoded)
│   └── LymphaFlow-Debug.xcconfig
├── LymphaFlow/
│   ├── App/
│   │   ├── LymphaFlowApp.swift    # @main, Purchases.configure()
│   │   └── ContentView.swift      # NavigationStack root
│   ├── Models/
│   │   ├── Routine.swift          # struct Routine: Identifiable, Codable
│   │   ├── Step.swift             # struct Step: Identifiable, Codable
│   │   └── SessionRecord.swift    # struct SessionRecord: Codable
│   ├── Services/
│   │   ├── SubscriptionServiceProtocol.swift
│   │   ├── SubscriptionService.swift   # RevenueCat実装
│   │   ├── SessionStore.swift          # UserDefaults CRUD
│   │   ├── NotificationService.swift   # UNUserNotificationCenter
│   │   └── RoutineDataService.swift    # routines.json loader
│   ├── ViewModels/
│   │   ├── OnboardingViewModel.swift
│   │   ├── HomeViewModel.swift
│   │   ├── TimerViewModel.swift
│   │   └── SettingsViewModel.swift
│   ├── Views/
│   │   ├── Onboarding/
│   │   │   ├── OnboardingView.swift
│   │   │   ├── OnboardingPageView.swift
│   │   │   └── NotificationPermissionView.swift
│   │   ├── Home/
│   │   │   ├── HomeView.swift
│   │   │   └── RoutineCardView.swift
│   │   ├── Session/
│   │   │   ├── SessionView.swift
│   │   │   └── StepView.swift
│   │   ├── Progress/
│   │   │   └── ProgressDashboardView.swift
│   │   ├── Settings/
│   │   │   └── SettingsView.swift
│   │   └── Paywall/
│   │       └── PaywallView.swift   # 自前SwiftUI（RC公式UIライブラリ禁止）
│   ├── Resources/
│   │   ├── Assets.xcassets/
│   │   ├── Localizable.xcstrings   # en-US + ja
│   │   ├── PrivacyInfo.xcprivacy
│   │   └── Data/
│   │       └── routines.json       # 静的コンテンツ
│   └── DesignSystem/
│       ├── Colors.swift            # Color tokens
│       ├── Typography.swift        # Font styles
│       └── Spacing.swift           # Spacing constants
└── LymphaFlowTests/
    └── (Unit + Integration tests)
```

---

## 4. Dependencies

Source: [RevenueCat SPM](https://www.revenuecat.com/docs/getting-started/installation/ios) — 「https://github.com/RevenueCat/purchases-ios」

| Package | Version | URL | Purpose |
|---------|---------|-----|---------|
| RevenueCat | 5.x | `https://github.com/RevenueCat/purchases-ios` | サブスクリプション管理 |

**禁止パッケージ（Greenlight CRITICAL）:**

| 禁止 | 理由 |
|------|------|
| RC公式UIライブラリ | Rule 20 — 自前PaywallView必須 |
| 分析SDK-A | Rule 17 — アナリティクスSDK禁止 |
| 分析SDK-B / 分析SDK-C | Rule 17 |
| 外部AIサービスA SDK | Rule 21 — AI API禁止 |
| 外部AIサービスB SDK | Rule 21 |
| 外部AIサービスC | Rule 21 |
| AppTrackingTransparency | Rule 20b — ATT禁止 |

---

## 5. Data Models

### Routine.swift

```swift
struct Routine: Identifiable, Codable {
    let id: String           // "face", "neck", "arm", etc.
    let titleKey: String     // Localizable.xcstrings key
    let descriptionKey: String
    let isPro: Bool          // false = Free tier (F-001)
    let programType: ProgramType  // morning, evening, standard
    let steps: [Step]
    let estimatedMinutes: Int
}

enum ProgramType: String, Codable {
    case morning, evening, standard
}
```

### Step.swift

```swift
struct Step: Identifiable, Codable {
    let id: String
    let titleKey: String         // Localizable key
    let descriptionKey: String
    let illustrationName: String // Assets.xcassets image name
    let durationSeconds: Int     // 30-60
}
```

### SessionRecord.swift

```swift
struct SessionRecord: Codable {
    let id: UUID
    let routineId: String
    let completedAt: Date
    let durationSeconds: Int
}
```

---

## 6. Services

### SubscriptionServiceProtocol.swift

```swift
protocol SubscriptionServiceProtocol: AnyObject {
    var isPro: Bool { get }
    func fetchOfferings() async throws -> Offerings
    func purchase(package: Package) async throws -> CustomerInfo
    func restorePurchases() async throws -> CustomerInfo
}
```

### SubscriptionService.swift (RevenueCat実装)

```swift
// Purchases.configure(withAPIKey: rcApiKey) — LymphaFlowApp.swift にて
// rcApiKey は Bundle.main.infoDictionary["RC_API_KEY"] から取得
// Feature F-005 Paywall と連携
```

### SessionStore.swift

```swift
// UserDefaults keys — §7参照
// CRUD: saveSession(_:), loadSessions() -> [SessionRecord]
// streakCount: Int (連続日数計算)
// F-004 セッション記録と連携
```

### NotificationService.swift

```swift
// UNUserNotificationCenter
// requestAuthorization() async -> Bool
// scheduleDailyReminder(hour: Int, minute: Int)
// cancelAllReminders()
// F-007 毎日リマインダーと連携
```

### RoutineDataService.swift

```swift
// routines.json を Bundle から読み込む（AI不使用、静的コンテンツ — Rule 21）
// func loadRoutines() -> [Routine]
// Free routines: id in ["face", "neck", "collarbone"] (F-001)
```

---

## 7. Storage

Source: [Apple Developer UserDefaults](https://developer.apple.com/documentation/foundation/userdefaults) — 「Simple key-value storage for lightweight data.」

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `lf.onboarding.completed` | Bool | false | オンボーディング完了フラグ（F-006）|
| `lf.sessions` | Data (JSON) | [] | SessionRecord配列（F-004）|
| `lf.streak.lastDate` | String (ISO8601) | "" | 最終セッション日（ストリーク計算）|
| `lf.streak.count` | Int | 0 | 連続日数（F-004）|
| `lf.notification.hour` | Int | 8 | 朝リマインダー時刻（F-007）|
| `lf.notification.evening.hour` | Int | 20 | 夜リマインダー時刻（F-007）|
| `lf.notification.enabled` | Bool | true | 通知ON/OFF（F-008）|

---

## 8. AI Integration

**Rule 21: AI API / AI モデル / 外部 AI サービス完全禁止。**

理由: 月額収益 $29 vs API コスト $300+。Apple の次世代AIフレームワークは iOS 26+ のみでユーザーベース皆無。

| 禁止 API | 禁止理由 |
|---------|---------|
| 外部AIサービスA API | Rule 21 + コスト発生 |
| 外部AIサービスB API | Rule 21 + コスト発生 |
| Google Generative AI | Rule 21 + コスト発生 |
| Apple AI Framework (iOS 26+) | Rule 21 + ユーザーベース皆無 |

**代替:** routines.json による静的キュレーションコンテンツ。全ステップ・説明はバンドル済み。

---

## 9. Networking

**外部API呼び出しなし。** アプリは完全自己完結（Rule 23）。

| 用途 | 方式 |
|------|------|
| ルーティンデータ | Bundle内 routines.json（オフライン動作）|
| サブスクリプション | RevenueCat SDK（インターネット接続時のみ検証）|
| バックエンド | なし |

---

## 10. Notifications

Source: [Apple Developer UNUserNotificationCenter](https://developer.apple.com/documentation/usernotifications/unusernotificationcenter) — 「Schedule local notifications without server dependency.」

| タイプ | スケジュール | Identifier |
|--------|-----------|-----------|
| Morning reminder | 毎日 8:00（デフォルト）| `lf.reminder.morning` |
| Evening reminder | 毎日 20:00（デフォルト）| `lf.reminder.evening` |

オンボーディング（NotificationPermissionView）で `requestAuthorization()` を呼び出す。ユーザーが拒否しても継続可（ソフトプロンプト）。

---

## 11. Privacy

Source: [Apple PrivacyInfo Requirements](https://developer.apple.com/news/releases/app-privacy-manifest-required-updates.html) — 「Required APIs must declare purpose codes.」

| 設定 | 値 |
|------|-----|
| PrivacyInfo.xcprivacy | 必須 |
| NSPrivacyAccessedAPITypes | `NSPrivacyAccessedAPICategoryUserDefaults: CA92.1` |
| サーバー送信データ | なし |
| ATT | **使用しない（Rule 20b）** |
| NSUserTrackingUsageDescription | **禁止（Rule 20b）** |
| ITSAppUsesNonExemptEncryption | false（Info.plist）|

---

## 12. Error Handling

| エラー種別 | ハンドリング | ユーザーメッセージ |
|----------|------------|----------------|
| RevenueCat purchase失敗 | `do-catch` → アラート表示 | "Purchase failed. Please try again." |
| RevenueCat restore失敗 | `do-catch` → アラート表示 | "Could not restore purchases." |
| JSON decode失敗（routines.json） | fatalError（開発時のみ）/ ログ出力 | — （静的データのため本番では発生しない）|
| 通知許可拒否 | 早期return（graceful degradation） | 設定から通知を有効にするよう案内 |
| オフライン（RevenueCat） | キャッシュ済み customerInfo を利用 | — |
