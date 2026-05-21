# Architecture: FrostDip

## 1. Platform Requirements

| Requirement | Value |
|-------------|-------|
| iOS Minimum | 17.0 |
| Xcode | 16.0+ |
| Swift | 5.9+ |
| Device | iPhone (portrait only for MVP) |
| bundle_id | com.aniccafactory.frostdip |

Source: [Apple SwiftData Documentation](https://developer.apple.com/documentation/swiftdata) — "Available in iOS 17.0+"

---

## 2. System Architecture Diagram

```
┌───────────────────────────────────────────────────┐
│                   App Layer                        │
│                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │  Views/   │ │ViewModels│ │  FrostDipApp     │  │
│  │  SwiftUI  │◄┤  MVVM    │ │  @main entry     │  │
│  └──────────┘ └────┬─────┘ └──────────────────┘  │
│                    │                               │
├────────────────────┼───────────────────────────────┤
│               Service Layer                        │
│                    │                               │
│  ┌─────────────┐ ┌┴────────────┐ ┌─────────────┐ │
│  │ TimerService │ │ HealthKit   │ │Subscription │ │
│  │ (Protocol)   │ │ Service     │ │ Service     │ │
│  │              │ │ (Protocol)  │ │ (Protocol)  │ │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ │
│         │               │               │         │
│  ┌──────┴──────┐ ┌──────┴──────┐ ┌──────┴──────┐ │
│  │Notification │ │             │ │             │ │
│  │ Service     │ │             │ │             │ │
│  │ (Protocol)  │ │             │ │             │ │
│  └─────────────┘ │             │ │             │ │
│                  │             │ │             │ │
├──────────────────┼─────────────┼─┼─────────────┼─┤
│              Data Layer        │ │             │ │
│                  │             │ │             │ │
│  ┌───────────┐ ┌┴───────────┐ │ │             │ │
│  │ SwiftData  │ │ HealthKit  │ │ │ RevenueCat  │ │
│  │ (Local DB) │ │ Store      │ │ │ SDK         │ │
│  └───────────┘ └────────────┘ │ └─────────────┘ │
│                               │                  │
│  ┌───────────┐ ┌────────────┐ │                  │
│  │UserDefaults│ │PrivacyInfo │ │                  │
│  │ (Prefs)   │ │ .xcprivacy │ │                  │
│  └───────────┘ └────────────┘ │                  │
│                               │                  │
└───────────────────────────────┴──────────────────┘
```

**Architecture Pattern:** MVVM (Model-View-ViewModel)

Source: [Apple SwiftUI Tutorials](https://developer.apple.com/tutorials/swiftui) — "SwiftUI works naturally with MVVM architecture"
Source: [Sundell](https://www.swiftbysundell.com/articles/different-flavors-of-view-models-in-swift/) — "ViewModels act as intermediaries between views and models"

---

## 3. Directory Structure

```
FrostDipios/
├── FrostDip/
│   ├── App/
│   │   ├── FrostDipApp.swift              # @main, ModelContainer, RevenueCat configure
│   │   └── AppState.swift                 # Tab selection, onboarding state
│   ├── Models/
│   │   ├── PlungeSession.swift            # @Model: duration, waterTemp, notes, heartRates, date
│   │   ├── PlungeProtocol.swift           # @Model: name, prepTime, coldTime, rounds, restTime
│   │   └── UserPreferences.swift          # Temperature unit, notification settings
│   ├── ViewModels/
│   │   ├── TimerViewModel.swift           # Timer countdown, HealthKit HR, session creation
│   │   ├── HistoryViewModel.swift         # Session queries, 7-day filter (free), full (premium)
│   │   ├── ProgressViewModel.swift        # Chart data aggregation
│   │   ├── OnboardingViewModel.swift      # Onboarding step management
│   │   ├── PaywallViewModel.swift         # RevenueCat offerings, purchase flow
│   │   └── SettingsViewModel.swift        # Preferences, subscription status
│   ├── Views/
│   │   ├── Timer/
│   │   │   ├── TimerView.swift            # F-001: Main countdown screen
│   │   │   ├── BreathingPrepView.swift    # F-002: Guided breathing animation
│   │   │   └── SessionSummaryView.swift   # Post-session stats
│   │   ├── History/
│   │   │   ├── HistoryView.swift          # F-004/F-008: Session list
│   │   │   └── SessionDetailView.swift    # Individual session detail
│   │   ├── Progress/
│   │   │   └── ProgressDashboardView.swift # F-011: Charts and stats
│   │   ├── Settings/
│   │   │   └── SettingsView.swift         # F-014: Preferences + upgrade
│   │   ├── Onboarding/
│   │   │   ├── OnboardingView.swift       # F-006: Onboarding container
│   │   │   └── PaywallView.swift          # F-013: Self-built paywall (Rule 20)
│   │   └── Components/
│   │       ├── StreakCalendarView.swift    # F-010: Visual streak calendar
│   │       ├── SessionCardView.swift      # Reusable session row
│   │       ├── PremiumBadgeView.swift     # Lock icon for premium features
│   │       └── CircularTimerView.swift    # Animated circular countdown
│   ├── Services/
│   │   ├── Protocols/
│   │   │   ├── HealthKitServiceProtocol.swift
│   │   │   ├── SubscriptionServiceProtocol.swift
│   │   │   ├── TimerServiceProtocol.swift
│   │   │   └── NotificationServiceProtocol.swift
│   │   ├── HealthKitService.swift         # F-007: HKHealthStore, heart rate queries
│   │   ├── SubscriptionService.swift      # F-013: RevenueCat Purchases wrapper
│   │   ├── TimerService.swift             # F-001: Foundation Timer + background
│   │   └── NotificationService.swift      # F-015: UNUserNotificationCenter
│   ├── Design/
│   │   ├── Theme.swift                    # DESIGN_SYSTEM color/typography tokens
│   │   ├── Colors.swift                   # Color asset references
│   │   └── Typography.swift               # Font scale definitions
│   ├── Resources/
│   │   ├── Localizable.xcstrings          # en-US + ja
│   │   └── PrivacyInfo.xcprivacy          # NSPrivacyAccessedAPICategoryUserDefaults
│   └── Config/
│       ├── Debug.xcconfig                 # RC_API_KEY for debug
│       └── Release.xcconfig               # RC_API_KEY for release
├── FrostDipTests/
│   ├── ViewModelTests/
│   ├── ServiceTests/
│   └── ModelTests/
├── FrostDipUITests/
├── maestro/                               # Maestro E2E flows
└── fastlane/
    └── Fastfile                           # fastlane lanes
```

---

## 4. Dependencies

| Package | Version | Purpose | SPM URL |
|---------|---------|---------|---------|
| RevenueCat Purchases | 5.x | Subscription management, entitlement checks | https://github.com/RevenueCat/purchases-ios.git |

**Prohibited Dependencies (CRITICAL):**

| Package | Rule | Reason |
|---------|------|--------|
| RevenueCatUI | Rule 20 | Must use self-built PaywallView |
| Mixpanel | Rule 17 | Analytics SDK prohibited |
| Firebase Analytics | Rule 17 | Analytics SDK prohibited |
| Any Analytics SDK | Rule 17 | Greenlight will detect and flag as CRITICAL |
| OpenAI SDK | Rule 21 | AI API cost prohibited ($300+ vs $29 revenue) |
| Anthropic SDK | Rule 21 | AI API cost prohibited |
| Google Generative AI | Rule 21 | AI API cost prohibited |
| Apple FoundationModels | Rule 21 | iOS 26+ only, negligible user base |

Source: [RevenueCat iOS SDK](https://www.revenuecat.com/docs/getting-started/installation/ios) — "Add via SPM: https://github.com/RevenueCat/purchases-ios.git"

---

## 5. Data Models

### PlungeSession (@Model — SwiftData)

```swift
@Model
final class PlungeSession {
    var id: UUID
    var date: Date
    var duration: TimeInterval          // total session seconds (cold phases summed)
    var waterTemperature: Double?       // Cold water Celsius (stored), displayed as C/F
    var hotTemperature: Double?         // Hot water Celsius (contrast therapy only)
    var notes: String
    var heartRateAvg: Double?           // BPM
    var heartRateMax: Double?           // BPM
    var heartRates: [Double]            // BPM samples array
    var protocolName: String?           // which protocol was used
    var isContrastSession: Bool         // true if contrast therapy
    var coldDuration: TimeInterval?     // per-round cold phase seconds (contrast only)
    var hotDuration: TimeInterval?      // per-round hot phase seconds (contrast only)
    var roundsCompleted: Int?           // rounds completed (contrast only)
    var createdAt: Date

    init(duration: TimeInterval, waterTemperature: Double? = nil, notes: String = "") {
        self.id = UUID()
        self.date = Date()
        self.duration = duration
        self.waterTemperature = waterTemperature
        self.notes = notes
        self.heartRates = []
        self.isContrastSession = false
        self.createdAt = Date()
    }
}
```

### PlungeProtocol (@Model — SwiftData)

```swift
@Model
final class PlungeProtocol {
    var id: UUID
    var name: String                    // "Beginner", "Intermediate", etc.
    var prepTime: TimeInterval          // breathing prep duration (seconds)
    var coldTime: TimeInterval          // cold plunge duration (seconds)
    var hotTime: TimeInterval           // hot phase duration (seconds, 0 for non-contrast)
    var rounds: Int                     // number of rounds (1 for simple, 2+ for contrast)
    var restTime: TimeInterval          // rest between rounds (seconds)
    var isDefault: Bool                 // true for built-in protocols
    var createdAt: Date

    init(name: String, prepTime: TimeInterval, coldTime: TimeInterval, hotTime: TimeInterval = 0, rounds: Int = 1, restTime: TimeInterval = 0) {
        self.id = UUID()
        self.name = name
        self.prepTime = prepTime
        self.coldTime = coldTime
        self.hotTime = hotTime
        self.rounds = rounds
        self.restTime = restTime
        self.isDefault = false
        self.createdAt = Date()
    }
}
```

### UserPreferences (UserDefaults-backed)

```swift
struct UserPreferences {
    var temperatureUnit: TemperatureUnit    // .celsius or .fahrenheit
    var notificationsEnabled: Bool
    var reminderTime: Date?                 // daily reminder time
    var hasCompletedOnboarding: Bool
    var experienceLevel: ExperienceLevel    // .beginner, .intermediate, .advanced
}

enum TemperatureUnit: String, Codable {
    case celsius, fahrenheit
}

enum ExperienceLevel: String, Codable {
    case beginner, intermediate, advanced
}
```

---

## 6. Services

### TimerService (F-001, F-002, F-012)

| Method | Signature | Description |
|--------|-----------|-------------|
| startTimer | `func startTimer(duration: TimeInterval, onTick: @escaping (TimeInterval) -> Void, onComplete: @escaping () -> Void)` | Start countdown with per-second callbacks |
| pauseTimer | `func pauseTimer()` | Pause active countdown |
| resumeTimer | `func resumeTimer()` | Resume paused countdown |
| stopTimer | `func stopTimer()` | Stop and reset timer |
| startBreathingPrep | `func startBreathingPrep(duration: TimeInterval, onPhaseChange: @escaping (BreathPhase) -> Void, onComplete: @escaping () -> Void)` | Guided breathing with inhale/exhale phases |

**Background Support:** Uses `BGTaskScheduler` for countdown continuation when app enters background. Schedules local notification for timer completion.

### HealthKitService (F-007)

| Method | Signature | Description |
|--------|-----------|-------------|
| requestAuthorization | `func requestAuthorization() async throws` | Request read permission for HKQuantityType.heartRate |
| startHeartRateMonitoring | `func startHeartRateMonitoring(onUpdate: @escaping (Double) -> Void)` | Start anchored query for live HR samples |
| stopHeartRateMonitoring | `func stopHeartRateMonitoring() -> (avg: Double?, max: Double?, samples: [Double])` | Stop monitoring, return aggregated data |
| isAvailable | `var isAvailable: Bool { get }` | Check if HealthKit is available on device |

Source: [Apple HealthKit](https://developer.apple.com/documentation/healthkit/hkanchoredObjectquery) — "Use anchored object queries for real-time health data updates"

### SubscriptionService (F-013)

| Method | Signature | Description |
|--------|-----------|-------------|
| configure | `func configure(apiKey: String)` | Initialize Purchases.shared |
| fetchOfferings | `func fetchOfferings() async throws -> [Package]` | Get available subscription packages |
| purchase | `func purchase(package: Package) async throws -> Bool` | Execute purchase via Purchases.shared.purchase(package:) |
| restorePurchases | `func restorePurchases() async throws -> Bool` | Restore previous purchases |
| isPremium | `var isPremium: Bool { get }` | Check "premium" entitlement status |
| listenForUpdates | `func listenForUpdates(onChange: @escaping (Bool) -> Void)` | Listen for entitlement changes |

Source: [RevenueCat iOS Quickstart](https://www.revenuecat.com/docs/getting-started/quickstart/ios) — "Use Purchases.shared.purchase(package:) for subscription purchases"

### NotificationService (F-015)

| Method | Signature | Description |
|--------|-----------|-------------|
| requestPermission | `func requestPermission() async throws -> Bool` | Request UNUserNotificationCenter authorization |
| scheduleReminder | `func scheduleReminder(at time: DateComponents, title: String, body: String)` | Schedule daily plunge reminder |
| scheduleStreakWarning | `func scheduleStreakWarning()` | Warn user if streak is about to break (evening) |
| cancelAll | `func cancelAll()` | Remove all pending notifications |

---

## 7. Storage

### UserDefaults Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `temperature_unit` | String | "celsius" | C/F preference |
| `notifications_enabled` | Bool | false | Reminder toggle |
| `reminder_time` | Double (TimeInterval) | nil | Daily reminder time |
| `has_completed_onboarding` | Bool | false | Onboarding gate |
| `experience_level` | String | "beginner" | User's cold plunge experience |
| `current_streak` | Int | 0 | Active daily streak count |
| `longest_streak` | Int | 0 | All-time longest streak |
| `last_plunge_date` | Double (TimeInterval) | nil | Date of most recent session |
| `streak_freeze_used_this_week` | Bool | false | Weekly streak freeze status |
| `app_launch_count` | Int | 0 | Launch counter (success metric) |

### SwiftData Storage

| Entity | Retention | Query Pattern |
|--------|-----------|---------------|
| PlungeSession | Indefinite (local) | By date (descending), filtered by 7-day (free) or unlimited (premium) |
| PlungeProtocol | Indefinite (local) | All protocols, sorted by createdAt |

---

## 8. AI Integration

**AI API / AI Model / External AI Service: NONE**

Rule 21: OpenAI, Anthropic, Google Generative AI, Apple FoundationModels are all prohibited.

| Rationale | Detail |
|-----------|--------|
| Economic | Monthly revenue $29 vs API cost $300+ — economically impossible |
| FoundationModels | iOS 26+ only — negligible user base makes it impractical |
| Alternative | All app logic is deterministic: timers, counters, streaks, HealthKit queries. No AI needed |

All content (protocols, tips, breathing patterns) is static and curated at build time.

---

## 9. Networking

| Endpoint | Purpose | When |
|----------|---------|------|
| RevenueCat API | Subscription management (handled by SDK) | App launch, purchase, restore |
| HealthKit | On-device health data (no network) | During active session |

**No custom backend.** No API calls except RevenueCat SDK (managed internally by the SDK). App is fully offline-capable after initial RevenueCat configuration.

---

## 10. Notifications

| Notification | Type | Trigger | Content |
|-------------|------|---------|---------|
| Daily Reminder | Local | User-configured time (DateComponents) | "Time for your cold plunge! Your streak is [N] days." |
| Streak Warning | Local | 8pm if no session today and streak > 0 | "Don't break your [N]-day streak! Plunge today." |
| Timer Complete | Local | Timer countdown reaches 0 (background) | "Session complete! [duration] in the cold." |

Source: [Apple UNUserNotificationCenter](https://developer.apple.com/documentation/usernotifications) — "Schedule local notifications using UNCalendarNotificationTrigger"

---

## 11. Privacy

### PrivacyInfo.xcprivacy

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
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
    <key>NSPrivacyCollectedDataTypes</key>
    <array/>
    <key>NSPrivacyTracking</key>
    <false/>
    <key>NSPrivacyTrackingDomains</key>
    <array/>
</dict>
</plist>
```

| Privacy Item | Value |
|-------------|-------|
| Data Collection | None (all local) |
| Tracking | false |
| ATT | NOT USED (Rule 20b) |
| HealthKit | Read-only (heart rate), declared in Info.plist with usage description |
| Third-party SDKs | RevenueCat only (their privacy manifest bundled in SDK) |

Source: [Apple Privacy Manifest](https://developer.apple.com/documentation/bundleresources/privacy_manifest_files)

---

## 12. Error Handling

| Error Type | Handling | User Message |
|-----------|---------|-------------|
| HealthKit not available | Graceful degradation — timer works without HR | "Heart rate monitoring not available on this device" |
| HealthKit permission denied | Show settings prompt | "Enable Health access in Settings to see heart rate" |
| HealthKit no HR data (30s timeout) | Timer works, HR section shows empty state | "No heart rate data detected. Pair an Apple Watch to monitor HR during plunges." |
| RevenueCat purchase failed | Show error alert, retry option | "Purchase failed. Please try again." |
| RevenueCat network error | Offline mode — use cached entitlement | "Unable to verify subscription. Using cached status." |
| Timer background interrupted | Save partial session | "Session saved (interrupted after [duration])" |
| SwiftData save failure | Retry once, then alert | "Unable to save session. Please try again." |
| Notification permission denied | Disable reminder UI, show settings link | "Enable notifications in Settings for plunge reminders" |

Source: [Apple Error Handling](https://developer.apple.com/documentation/swift/error) — "Use do-catch blocks for recoverable errors, present user-friendly messages"
