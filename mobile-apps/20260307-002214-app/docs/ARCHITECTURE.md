# Architecture: EyeBreakIsland

**Version:** 1.0
**Date:** 2026-03-07
**SSOT:** docs/PRD.md

Source: [Apple Developer: ActivityKit](https://developer.apple.com/documentation/activitykit) — "Display your app's data in Dynamic Island and on the Lock Screen with Live Activities"
Source: [Apple HIG: Live Activities](https://developer.apple.com/design/human-interface-guidelines/live-activities) — "Keep your Live Activity focused and glanceable"
Source: [SwiftUI App Architecture (WWDC22)](https://developer.apple.com/videos/play/wwdc2022/10054/) — "Use observable models for state management"

---

## 1. Platform Requirements

| Requirement | Value |
|-------------|-------|
| iOS Minimum | 16.1 (ActivityKit) |
| Xcode | 16.0+ |
| Swift | 5.9+ |
| UI Framework | SwiftUI |
| bundle_id | com.aniccafactory.eyebreakisland |
| Deployment Target | iPhone only (iPad: v1.2) |
| Device Focus | iPhone 14 Pro+ (Dynamic Island) with fallback for non-Dynamic-Island devices |

---

## 2. System Architecture Diagram

```
┌──────────────────────────────────────────────────┐
│                    App Layer                       │
│  ┌────────────┐ ┌────────────┐ ┌──────────────┐  │
│  │ Onboarding │ │  Timer     │ │  Settings    │  │
│  │ Views      │ │  Views     │ │  Views       │  │
│  └─────┬──────┘ └─────┬──────┘ └──────┬───────┘  │
│        │              │               │           │
│  ┌─────▼──────┐ ┌─────▼──────┐ ┌──────▼───────┐  │
│  │ Onboarding │ │  Timer     │ │  Settings    │  │
│  │ ViewModel  │ │  ViewModel │ │  ViewModel   │  │
│  └─────┬──────┘ └─────┬──────┘ └──────┬───────┘  │
├────────┼──────────────┼───────────────┼───────────┤
│                  Service Layer                     │
│  ┌──────────────┐ ┌──────────────┐ ┌───────────┐ │
│  │ TimerService │ │ Notification │ │Subscription│ │
│  │              │ │ Service      │ │ Service    │ │
│  └──────┬───────┘ └──────┬───────┘ └─────┬─────┘ │
│         │                │               │        │
│  ┌──────▼───────┐ ┌──────▼───────┐ ┌─────▼─────┐ │
│  │ ActivityKit  │ │ UNUserNotif  │ │ RevenueCat│ │
│  │ (Live Act.)  │ │ Center       │ │ SDK       │ │
│  └──────────────┘ └──────────────┘ └───────────┘ │
├───────────────────────────────────────────────────┤
│                   Data Layer                       │
│  ┌──────────────┐ ┌──────────────┐               │
│  │ UserDefaults │ │ Models       │               │
│  │ (Settings,   │ │ (TimerState, │               │
│  │  Stats)      │ │  BreakSession│               │
│  └──────────────┘ └──────────────┘               │
└───────────────────────────────────────────────────┘
```

**Pattern:** MVVM (Model-View-ViewModel)

Source: [SwiftUI App Architecture (WWDC22)](https://developer.apple.com/videos/play/wwdc2022/10054/) — "Model your data, define your sources of truth, compose your views"

---

## 3. Directory Structure

```
EyeBreakIslandios/
├── EyeBreakIsland/
│   ├── App/
│   │   └── EyeBreakIslandApp.swift          # @main, RevenueCat Purchases.configure
│   ├── xcconfig/
│   │   └── Config.xcconfig                  # RC_PUBLIC_KEY (not hardcoded)
│   ├── Models/
│   │   ├── TimerState.swift                 # enum: idle, running, breaking, paused
│   │   ├── BreakSession.swift               # struct: startedAt, breakCount, date
│   │   └── SubscriptionStatus.swift         # enum: free, pro
│   ├── Services/
│   │   ├── TimerService.swift               # Timer logic + Live Activity management
│   │   ├── NotificationService.swift        # UNUserNotificationCenter wrapper
│   │   └── SubscriptionService.swift        # Protocol + RevenueCat implementation
│   ├── ViewModels/
│   │   ├── OnboardingViewModel.swift        # Onboarding state machine
│   │   ├── TimerViewModel.swift             # Timer UI state + user actions
│   │   ├── PaywallViewModel.swift           # Package loading + purchase flow
│   │   └── SettingsViewModel.swift          # Settings state management
│   ├── Views/
│   │   ├── Onboarding/
│   │   │   ├── OnboardingContainerView.swift
│   │   │   ├── OnboardingPageView.swift
│   │   │   └── PaywallView.swift            # Custom SwiftUI (Rule 20)
│   │   ├── Timer/
│   │   │   ├── TimerView.swift              # Main screen
│   │   │   └── BreakOverlayView.swift       # Full-screen 20-sec countdown
│   │   └── Settings/
│   │       └── SettingsView.swift
│   ├── LiveActivity/
│   │   ├── EyeBreakAttributes.swift         # ActivityAttributes definition
│   │   └── EyeBreakWidgetBundle.swift       # Widget extension entry
│   ├── Utilities/
│   │   └── Constants.swift                  # App-wide constants
│   ├── Resources/
│   │   ├── Localizable.xcstrings            # en-US + ja
│   │   ├── PrivacyInfo.xcprivacy            # UserDefaults CA92.1
│   │   └── Assets.xcassets                  # App icon, colors
│   └── Info.plist
├── EyeBreakIslandTests/
│   ├── TimerServiceTests.swift
│   ├── NotificationServiceTests.swift
│   ├── SubscriptionServiceTests.swift
│   ├── TimerViewModelTests.swift
│   └── OnboardingViewModelTests.swift
├── EyeBreakIslandWidgetExtension/
│   ├── EyeBreakLiveActivityView.swift       # Dynamic Island + Lock Screen UI
│   └── Info.plist
└── fastlane/
    └── Fastfile
```

---

## 4. Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **RevenueCat (Purchases)** | ~> 5.0 | Subscription management via `Purchases.shared.purchase(package:)` |

**Explicitly Prohibited:**

| Package | Rule | Reason |
|---------|------|--------|
| RevenueCatUI | Rule 20 | Must use custom SwiftUI PaywallView |
| Mixpanel | Rule 17 | No analytics SDK |
| Firebase Analytics | Rule 17 | No analytics SDK |
| OpenAI SDK | Rule 21 | No AI API — app is fully self-contained |
| Anthropic SDK | Rule 21 | No AI API |
| GoogleGenerativeAI | Rule 21 | No AI API |
| Apple FoundationModels | Rule 21 | iOS 26+ only, user base too small |

Source: [RevenueCat iOS SDK](https://github.com/RevenueCat/purchases-ios) — "The official RevenueCat SDK for iOS"

---

## 5. Data Models

### TimerState

```swift
enum TimerState: String, Codable {
    case idle       // Timer not started
    case running    // 20-min countdown active
    case breaking   // 20-sec eye rest active
    case paused     // Timer paused by user
}
```

### BreakSession

```swift
struct BreakSession: Codable, Identifiable {
    let id: UUID
    let date: Date           // Session date
    var breakCount: Int      // Number of completed breaks
    var totalMinutes: Int    // Total active timer minutes
}
```

### SubscriptionStatus

```swift
enum SubscriptionStatus: String, Codable {
    case free
    case pro
}
```

### EyeBreakAttributes (ActivityKit)

```swift
struct EyeBreakAttributes: ActivityAttributes {
    public struct ContentState: Codable, Hashable {
        var timerState: String     // "running" or "breaking"
        var remainingSeconds: Int  // Seconds left in current phase
        var breakCount: Int        // Breaks completed today
    }
    var sessionId: String
}
```

---

## 6. Services

### TimerService (F-001, F-002)

| Method | Signature | Description |
|--------|-----------|-------------|
| startSession | `func startSession()` | Begin 20-min countdown + start Live Activity |
| stopSession | `func stopSession()` | Stop timer + end Live Activity |
| pauseSession | `func pauseSession()` | Pause current countdown |
| resumeSession | `func resumeSession()` | Resume paused countdown |
| startBreak | `func startBreak()` | Transition to 20-sec break phase |
| completeBreak | `func completeBreak()` | End break, increment counter, restart 20-min timer |
| updateLiveActivity | `func updateLiveActivity(state: EyeBreakAttributes.ContentState)` | Push state to Dynamic Island |

**Protocol:**

```swift
protocol TimerServiceProtocol {
    var timerState: TimerState { get }
    var remainingSeconds: Int { get }
    var breakCount: Int { get }
    func startSession()
    func stopSession()
    func pauseSession()
    func resumeSession()
}
```

### NotificationService (F-003)

| Method | Signature | Description |
|--------|-----------|-------------|
| requestPermission | `func requestPermission() async -> Bool` | Request notification authorization |
| scheduleBreakNotification | `func scheduleBreakNotification(after: TimeInterval)` | Schedule a break reminder |
| cancelAll | `func cancelAll()` | Remove all pending notifications |

**Protocol:**

```swift
protocol NotificationServiceProtocol {
    func requestPermission() async -> Bool
    func scheduleBreakNotification(after: TimeInterval)
    func cancelAll()
}
```

### SubscriptionService (F-005, F-006, F-007, F-008)

| Method | Signature | Description |
|--------|-----------|-------------|
| configure | `func configure(apiKey: String)` | Initialize RevenueCat SDK |
| loadOfferings | `func loadOfferings() async throws -> [Package]` | Fetch available packages |
| purchase | `func purchase(package: Package) async throws -> Bool` | Execute purchase |
| restorePurchases | `func restorePurchases() async throws -> SubscriptionStatus` | Restore previous purchases |
| checkStatus | `func checkStatus() async -> SubscriptionStatus` | Check current entitlement |

**Protocol:**

```swift
protocol SubscriptionServiceProtocol {
    var status: SubscriptionStatus { get }
    func configure(apiKey: String)
    func loadOfferings() async throws -> [Package]
    func purchase(package: Package) async throws -> Bool
    func restorePurchases() async throws -> SubscriptionStatus
    func checkStatus() async -> SubscriptionStatus
}
```

Source: [RevenueCat: Getting Started](https://www.revenuecat.com/docs/getting-started/quickstart/ios) — "Purchases.shared.purchase(package:)"

---

## 7. Storage

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `hasCompletedOnboarding` | Bool | false | Skip onboarding on subsequent launches |
| `timerIntervalMinutes` | Int | 20 | Work interval duration (Pro: 15/20/25) |
| `breakDurationSeconds` | Int | 20 | Break duration (fixed in Free) |
| `notificationsEnabled` | Bool | true | User preference for notifications |
| `todayBreakCount` | Int | 0 | Breaks completed today (reset daily) |
| `currentStreak` | Int | 0 | Consecutive days with 1+ breaks |
| `lastActiveDate` | String | "" | ISO8601 date for streak calculation |
| `scheduleStartHour` | Int | 9 | Pro: schedule start hour |
| `scheduleEndHour` | Int | 18 | Pro: schedule end hour |
| `scheduleEnabled` | Bool | false | Pro: schedule mode active |

**All data stored locally. No cloud sync. No server.**

---

## 8. AI Integration

**None.** Rule 21 prohibits all AI APIs and external AI services.

| Prohibited | Reason |
|-----------|--------|
| OpenAI API | Monthly revenue $29 vs API cost $300+ |
| Anthropic API | Same cost concern |
| Google Generative AI | Same cost concern |
| Apple FoundationModels | iOS 26+ only — user base too small in 2026 |

The app is fully self-contained. All logic runs on-device. Timer calculations, streak tracking, and break scheduling are pure Swift code with no external dependencies beyond RevenueCat for subscription management.

---

## 9. Networking

| Endpoint | Purpose | Frequency |
|----------|---------|-----------|
| RevenueCat API (automatic) | Subscription validation, offerings fetch | On app launch + purchase |

**No custom backend.** No REST API. No WebSocket. RevenueCat SDK handles all server communication transparently.

---

## 10. Notifications

### Strategy

| Trigger | Type | Content |
|---------|------|---------|
| 20-min timer elapsed (app foreground) | Live Activity update | Dynamic Island transitions to "break" state |
| 20-min timer elapsed (app background) | UNNotificationRequest | "Time for a 20-second eye break!" |
| Break completed | Live Activity update | Dynamic Island resets to next 20-min countdown |
| Daily reminder (if no breaks today) | UNNotificationRequest (scheduled) | "Your eyes need a break. Start your timer." |

### Implementation

```swift
// Background notification scheduling
let content = UNMutableNotificationContent()
content.title = String(localized: "timer.break.title")
content.body = String(localized: "timer.break.instruction")
content.sound = .default

let trigger = UNTimeIntervalNotificationTrigger(
    timeInterval: 20 * 60,  // 20 minutes
    repeats: false
)

let request = UNNotificationRequest(
    identifier: "eyebreak-\(UUID().uuidString)",
    content: content,
    trigger: trigger
)
```

Source: [Apple Developer: UserNotifications](https://developer.apple.com/documentation/usernotifications) — "Schedule and handle local and remote notifications"

---

## 11. Privacy

### PrivacyInfo.xcprivacy

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSPrivacyTracking</key>
    <false/>
    <key>NSPrivacyTrackingDomains</key>
    <array/>
    <key>NSPrivacyCollectedDataTypes</key>
    <array/>
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
</dict>
</plist>
```

| Privacy Item | Value |
|-------------|-------|
| Tracking | false |
| Tracking Domains | none |
| Collected Data Types | none |
| ATT | NOT USED (Rule 20b) |
| Accessed APIs | UserDefaults (CA92.1) |

Source: [Apple: Privacy Manifest Files](https://developer.apple.com/documentation/bundleresources/privacy_manifest_files) — "Apps must declare API usage reasons"

---

## 12. Error Handling

| Error Type | Handling | User Message |
|-----------|----------|-------------|
| Live Activity start failure | Fallback to notification-only mode | "Dynamic Island unavailable. Using notifications instead." |
| Notification permission denied | Show in-app break overlay only | "Enable notifications in Settings for background reminders." |
| RevenueCat purchase failure | Show error alert, allow retry | "Purchase failed. Please try again." |
| RevenueCat network error | Use cached subscription status | (silent — cached status used) |
| Live Activity limit exceeded | Log warning, use notification fallback | "Too many active widgets. Timer will use notifications." |
| UserDefaults read failure | Use default values | (silent — defaults used) |

Source: [Apple Developer: Handling Errors](https://developer.apple.com/documentation/activitykit/displaying-live-data-with-live-activities#Handle-errors) — "Your app should handle situations where the system denies the request to start a Live Activity"

---

## 13. Coding Style Exceptions

| Exception | Scope | Reason |
|-----------|-------|--------|
| `@Published` property mutation | All `ObservableObject` ViewModels and Services | SwiftUI observation requires mutable `@Published` properties on reference types. Immutability rule applies to value types and function parameters, not to `ObservableObject` state management. |

---

**End of Architecture**
