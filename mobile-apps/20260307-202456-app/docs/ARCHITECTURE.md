# Architecture: EyeRest

## 1. Platform Requirements

| Requirement | Value |
|-------------|-------|
| iOS Minimum | 17.0 |
| Xcode | 16.0+ |
| Swift | 5.9+ |
| Framework | SwiftUI |
| Architecture | MVVM + Protocol DI |
| bundle_id | com.aniccafactory.eyerest |

Source: [Apple SwiftUI Documentation](https://developer.apple.com/documentation/swiftui) — SwiftUI is the recommended declarative UI framework for new iOS apps
Source: product-plan.md §5 Technical Architecture

---

## 2. System Architecture Diagram

```
┌──────────────────────────────────────────────────────┐
│                    Presentation Layer                  │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────────┐  │
│  │  TimerView   │ │ ExerciseList │ │  StatsView    │  │
│  │  RestView    │ │ ExerciseDetail│ │  SettingsView │  │
│  │  OnboardView │ │              │ │  PaywallView  │  │
│  └──────┬──────┘ └──────┬───────┘ └──────┬────────┘  │
│         │               │                │            │
│  ┌──────▼──────┐ ┌──────▼───────┐ ┌──────▼────────┐  │
│  │ TimerVM     │ │ ExerciseVM   │ │  StatsVM      │  │
│  │ OnboardingVM│ │              │ │  SettingsVM   │  │
│  │             │ │              │ │  PaywallVM    │  │
│  └──────┬──────┘ └──────┬───────┘ └──────┬────────┘  │
└─────────┼───────────────┼────────────────┼────────────┘
          │               │                │
┌─────────▼───────────────▼────────────────▼────────────┐
│                     Service Layer                      │
│  ┌────────────────┐ ┌──────────────────────────────┐  │
│  │ TimerService   │ │ SubscriptionService          │  │
│  │(TimerSvcProto) │ │ (SubscriptionServiceProtocol)│  │
│  └───────┬────────┘ └──────────────┬───────────────┘  │
│  ┌───────▼────────┐                │                  │
│  │NotificationSvc │                │                  │
│  │(NotifSvcProto) │                │                  │
│  └───────┬────────┘                │                  │
└──────────┼─────────────────────────┼──────────────────┘
           │                         │
┌──────────▼─────────────────────────▼──────────────────┐
│                      Data Layer                        │
│  ┌──────────────┐  ┌──────────┐  ┌─────────────────┐  │
│  │  SwiftData   │  │UserDefaults│ │  RevenueCat    │  │
│  │(BreakSession,│  │(Settings) │ │  (Purchases)   │  │
│  │ FatigueEntry)│  │           │ │                 │  │
│  └──────────────┘  └──────────┘  └─────────────────┘  │
└────────────────────────────────────────────────────────┘
```

Source: [Apple App Architecture Guide](https://developer.apple.com/documentation/swiftui/model-data) — "Separate your app's data model from its views"

---

## 3. Directory Structure

```
EyeRestios/
├── EyeRest/
│   ├── App/
│   │   ├── EyeRestApp.swift              # @main, RevenueCat configure, SwiftData container
│   │   └── AppDelegate.swift             # BGTaskScheduler registration
│   ├── Models/
│   │   ├── BreakSession.swift            # SwiftData @Model — break completion record
│   │   ├── FatigueEntry.swift            # SwiftData @Model — fatigue self-report
│   │   └── EyeExercise.swift             # Static struct — exercise content data
│   ├── ViewModels/
│   │   ├── TimerViewModel.swift          # Timer countdown, background state, notifications
│   │   ├── OnboardingViewModel.swift     # Onboarding step tracking, completion state
│   │   ├── SettingsViewModel.swift       # User preferences, premium gating
│   │   ├── StatsViewModel.swift          # Break stats, fatigue charts, streak calc
│   │   ├── ExerciseViewModel.swift       # Exercise list, detail, premium lock
│   │   └── PaywallViewModel.swift        # RevenueCat offerings, purchase flow
│   ├── Views/
│   │   ├── TimerView.swift               # Main timer screen (F-001)
│   │   ├── RestView.swift                # 20-sec rest countdown (F-002)
│   │   ├── ExerciseListView.swift        # Exercise library (F-005, F-008)
│   │   ├── ExerciseDetailView.swift      # Individual exercise detail
│   │   ├── StatsView.swift               # Daily/weekly stats (F-004, F-011)
│   │   ├── SettingsView.swift            # Settings screen (F-012)
│   │   ├── OnboardingView.swift          # Onboarding flow (F-006)
│   │   └── PaywallView.swift             # Subscription paywall (F-013, Rule 20)
│   ├── Components/
│   │   ├── TimerRing.swift               # Circular progress indicator (DESIGN_SYSTEM §4)
│   │   ├── BreakCountBadge.swift         # Daily break counter with streak
│   │   ├── ExerciseCard.swift            # Exercise preview card
│   │   ├── FatigueLevelPicker.swift      # 1-5 scale selector with face icons
│   │   ├── PremiumBadge.swift            # "PRO" label for premium features
│   │   ├── StatCard.swift               # Metric display card
│   │   ├── WeeklyChart.swift            # 7-day bar chart
│   │   ├── PlanToggle.swift             # Monthly/Annual subscription toggle
│   │   ├── FeatureRow.swift             # Paywall feature benefit row
│   │   └── OnboardingPage.swift         # Single onboarding page template
│   ├── Services/
│   │   ├── TimerService.swift            # BackgroundTasks + timer management
│   │   ├── NotificationService.swift     # UNUserNotificationCenter scheduling
│   │   └── SubscriptionService.swift     # RevenueCat wrapper (Protocol DI)
│   ├── Protocols/
│   │   ├── SubscriptionServiceProtocol.swift  # Subscription abstraction for testability
│   │   ├── NotificationServiceProtocol.swift  # Notification abstraction for testability
│   │   └── TimerServiceProtocol.swift         # Timer abstraction for testability
│   ├── Resources/
│   │   ├── Localizable.xcstrings         # en-US + ja String Catalogs
│   │   ├── Assets.xcassets               # App icons, colors, images
│   │   └── PrivacyInfo.xcprivacy         # Privacy manifest
│   └── Config/
│       ├── Debug.xcconfig                # RC_API_KEY for debug builds
│       └── Release.xcconfig              # RC_API_KEY for release builds
├── EyeRestTests/
│   ├── TimerViewModelTests.swift
│   ├── StatsViewModelTests.swift
│   ├── SubscriptionServiceTests.swift
│   ├── BreakSessionTests.swift
│   ├── FatigueEntryTests.swift
│   ├── OnboardingViewModelTests.swift
│   ├── PaywallViewModelTests.swift
│   └── EyeExerciseTests.swift
├── maestro/
│   ├── onboarding.yaml
│   ├── timer.yaml
│   ├── settings.yaml
│   ├── payment-monthly.yaml
│   ├── payment-annual.yaml
│   └── payment-failure.yaml
└── fastlane/
    └── Fastfile
```

---

## 4. Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| RevenueCat/purchases-ios | ~> 5.0 | Subscription management — `Purchases.shared.purchase(package:)` |

**Prohibited Dependencies (CRITICAL):**

| Package | Rule | Reason |
|---------|------|--------|
| RC UI module | Rule 20 | Custom PaywallView required — RC UI import is forbidden |
| Third-party telemetry | Rule 17 | Tracking SDK prohibited — Greenlight will detect and flag CRITICAL |
| Google telemetry | Rule 17 | Tracking SDK prohibited |
| Any tracking SDK | Rule 17 | No telemetry SDKs of any kind |
| Third-party AI SDKs | Rule 23 | AI API costs prohibited — monthly revenue $29 vs API costs $300+ |
| All AI vendor SDKs | Rule 23 | AI API costs prohibited |
| Google AI SDK | Rule 23 | AI API costs prohibited |
| Apple on-device ML (iOS 26+) | Rule 23 | iOS 26+ only — user base too small |

Source: [RevenueCat iOS SDK Docs](https://www.revenuecat.com/docs/getting-started/installation/ios) — SPM integration
Source: CLAUDE.md Rules 17, 20, 20b, 23

---

## 5. Data Models

### BreakSession (SwiftData @Model)

```swift
@Model
final class BreakSession {
    var id: UUID                    // Unique identifier
    var startedAt: Date             // When the break started
    var completedAt: Date           // When the 20-sec rest finished
    var intervalMinutes: Int         // Timer interval used (10-30)
    // Fatigue data is stored in FatigueEntry (linked via sessionId) — no duplication

    init(intervalMinutes: Int = 20) {
        self.id = UUID()
        self.startedAt = Date()
        self.completedAt = Date()
        self.intervalMinutes = intervalMinutes
    }
}
```

### FatigueEntry (SwiftData @Model)

```swift
@Model
final class FatigueEntry {
    var id: UUID
    var recordedAt: Date
    var level: Int                   // 1-5 scale (1=fine, 5=severe)
    var sessionId: UUID?             // Link to BreakSession

    init(level: Int, sessionId: UUID? = nil) {
        self.id = UUID()
        self.recordedAt = Date()
        self.level = level
        self.sessionId = sessionId
    }
}
```

### EyeExercise (Static Struct)

```swift
struct EyeExercise: Identifiable, Codable {
    let id: String                  // e.g. "palming"
    let nameKey: String             // Localization key
    let descriptionKey: String      // Localization key
    let durationSeconds: Int        // Exercise duration
    let isPremium: Bool             // Free (palming) or Premium
    let steps: [String]             // Localization keys for step instructions
}
```

### Exercise Content (Static Data — F-005, F-008)

| ID | Exercise | Duration | Tier |
|----|----------|----------|------|
| palming | Palming | 60s | Free |
| figure_eight | Figure-8 | 45s | Premium |
| near_far_focus | Near-Far Focus | 60s | Premium |
| extended_20_20_20 | 20-20-20 Extended | 30s | Premium |
| blink_drill | Blink Drill | 30s | Premium |
| pencil_push_up | Pencil Push-Up | 45s | Premium |
| eye_rolling | Eye Rolling | 30s | Premium |
| temple_massage | Temple Massage | 60s | Premium |

---

## 6. Services

### TimerService

| Method | Signature | Description |
|--------|-----------|-------------|
| startTimer | `func startTimer(intervalMinutes: Int)` | Start countdown, schedule background task |
| pauseTimer | `func pauseTimer()` | Pause running timer, clear targetFireDate |
| resumeTimer | `func resumeTimer()` | Resume paused timer from remainingSeconds |
| stopTimer | `func stopTimer()` | Cancel running timer and background task |
| scheduleBackgroundRefresh | `func scheduleBackgroundRefresh(in: TimeInterval)` | Register BGAppRefreshTaskRequest for next break |
| handleBackgroundTask | `func handleBackgroundTask(_ task: BGTask)` | Fire notification and reschedule |
| handleBackgroundTransition | `func handleBackgroundTransition()` | Save targetFireDate to UserDefaults, invalidate Timer, rely on notification |
| handleForegroundTransition | `func handleForegroundTransition()` | Restore from saved targetFireDate, resume or trigger rest |

### NotificationService (NotificationServiceProtocol)

| Method | Signature | Description |
|--------|-----------|-------------|
| requestPermission | `func requestPermission() async -> Bool` | Request UNUserNotificationCenter authorization |
| scheduleBreakNotification | `func scheduleBreakNotification(in seconds: TimeInterval)` | Schedule local notification for next break |
| fireImmediateBreakNotification | `func fireImmediateBreakNotification()` | Fire notification immediately (nil trigger) |
| cancelAllNotifications | `func cancelAllNotifications()` | Remove all pending notifications |
| checkPermissionStatus | `func checkPermissionStatus() async -> UNAuthorizationStatus` | Check current notification authorization |

### SubscriptionService (Protocol DI — F-013)

| Method | Signature | Description |
|--------|-----------|-------------|
| configure | `func configure(apiKey: String)` | Initialize RevenueCat SDK |
| fetchOfferings | `func fetchOfferings() async throws -> [Package]` | Get available subscription packages |
| purchase | `func purchase(package: Package) async throws -> PurchaseResult` | Execute `Purchases.shared.purchase(package:)` |
| restorePurchases | `func restorePurchases() async throws -> CustomerInfo` | Restore prior purchases |
| isPremium | `var isPremium: Bool { get }` | Check current entitlement status |
| customerInfoStream | `var customerInfoStream: AsyncStream<CustomerInfo> { get }` | Listen for entitlement changes |

---

## 7. Storage

### UserDefaults Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `hasCompletedOnboarding` | Bool | false | Skip onboarding after completion |
| `timerIntervalMinutes` | Int | 20 | User's preferred timer interval |
| `isTimerEnabled` | Bool | true | Global timer on/off toggle |
| `workingHoursStart` | Int | 9 | Working hours start (hour, 0-23) |
| `workingHoursEnd` | Int | 18 | Working hours end (hour, 0-23) |
| `isWorkingHoursEnabled` | Bool | false | Working hours schedule on/off |
| `currentStreak` | Int | 0 | Consecutive days with 4+ breaks |
| `lastActiveDate` | String | "" | ISO date for streak calculation |
| `notificationSoundEnabled` | Bool | true | Notification sound on/off |

### SwiftData (Local Only)

| Entity | Storage | Retention |
|--------|---------|-----------|
| BreakSession | SwiftData ModelContainer | Indefinite (local) |
| FatigueEntry | SwiftData ModelContainer | Indefinite (local) |

**No CloudKit. No remote sync. All data stays on device.**

---

## 8. AI Integration

**Rule 23: AI API / AI Model / External AI Service — COMPLETELY PROHIBITED.**

| Prohibited | Reason |
|-----------|--------|
| Third-party AI API (all vendors) | Monthly revenue $29 vs API costs $300+ |
| All cloud AI inference APIs | Same cost concern |
| Google Generative AI | Same cost concern |
| Apple on-device ML framework | iOS 26+ only — user base too small in 2026 |
| Any on-device ML model | Not needed — timer + static content is sufficient |

EyeRest uses only static, curated content for eye exercises and health tips. No AI generation, no inference, no ML models.

---

## 9. Networking

| Endpoint | Service | Direction | Purpose |
|----------|---------|-----------|---------|
| RevenueCat API | SubscriptionService | Outbound | Subscription verification, offerings fetch, purchase |

**No custom backend. No REST API. No WebSocket.** RevenueCat is the only external service.

---

## 10. Notifications

### Local Notification Strategy

```
┌──────────────┐    20 min    ┌──────────────────┐
│ Timer Start  │────────────>│ Local Notification │
│              │             │ "Time for a break" │
└──────────────┘             └────────┬───────────┘
                                      │
                              ┌───────▼────────┐
                              │ User taps notif │
                              │ → RestView opens│
                              └───────┬────────┘
                                      │
                              ┌───────▼────────┐
                              │ 20-sec rest     │
                              │ → Timer resets  │
                              └────────────────┘
```

| Aspect | Implementation |
|--------|---------------|
| Framework | UNUserNotificationCenter |
| Trigger | UNTimeIntervalNotificationTrigger (interval × 60 seconds) |
| Background | BGAppRefreshTaskRequest as fallback for timer expiration |
| Foreground | In-app alert/overlay when timer fires while app is active |
| Sound | Default system notification sound (respects silent mode) |
| Badge | Not used |
| Categories | `eyerest.break` — with "Start Break" action button |

Source: [Apple UNUserNotificationCenter](https://developer.apple.com/documentation/usernotifications/unusernotificationcenter) — local notification scheduling
Source: [Apple BackgroundTasks](https://developer.apple.com/documentation/backgroundtasks) — BGAppRefreshTaskRequest

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
| Tracking | NO (NSPrivacyTracking = false) |
| Tracking Domains | None |
| Collected Data Types | None |
| ATT (Rule 20b) | NOT USED — no app tracking transparency API, no NSUserTrackingUsageDescription |
| Accessed APIs | UserDefaults (CA92.1) only |

---

## 12. Error Handling

| Error Type | Handling | User Message |
|-----------|---------|-------------|
| Notification Permission Denied | Show settings deep-link banner | "Enable notifications in Settings to get eye break reminders" |
| RevenueCat Fetch Failure | Retry with exponential backoff (3 attempts) | "Unable to load subscription options. Please try again." |
| Purchase Failed | Show error from RevenueCat error description | "Purchase could not be completed. Please try again." |
| Purchase Cancelled | Silent dismissal — no error shown | (none) |
| Restore Failed | Show alert with retry option | "Could not restore purchases. Please try again." |
| SwiftData Save Failure | Log error, continue without persistence | (none — silent degradation) |
| Background Task Not Scheduled | Fall back to scheduled local notifications only | (none — transparent fallback) |
| Timer Drift (>30s) | Accept drift — health reminder, not precision timer | (none — acceptable tolerance) |

Source: [RevenueCat Error Handling](https://www.revenuecat.com/docs/getting-started/making-purchases#handling-errors) — purchase error types and recommended handling
