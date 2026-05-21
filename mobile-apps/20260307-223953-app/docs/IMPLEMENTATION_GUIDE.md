# Implementation Guide: FrostDip

## 1. Prerequisites

### Development Environment

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Xcode | 16.0+ | IDE, Swift compiler, simulator |
| Swift | 5.9+ | Language |
| iOS Simulator | iPhone 15 Pro (iOS 17.0+) | Development testing |
| fastlane | Latest | Build automation |
| Maestro | Latest | E2E testing |

### Xcode Project Setup

```bash
# 1. Create Xcode project
# Target: iOS App, SwiftUI lifecycle, Swift language
# Product Name: FrostDip
# Organization Identifier: com.aniccafactory
# Bundle Identifier: com.aniccafactory.frostdip
# Storage: SwiftData
# Include Tests: Yes

# 2. Add SPM dependency
# File > Add Package Dependencies
# URL: https://github.com/RevenueCat/purchases-ios.git
# Version: Up to Next Major 5.x
# Product: RevenueCat (NOT RevenueCatUI)
```

### Xcode Signing

| Setting | Value |
|---------|-------|
| Team | Anicca Factory team (set in ASC) |
| Signing | Automatic |
| Provisioning Profile | Managed by Xcode |
| Bundle ID | com.aniccafactory.frostdip |

### RevenueCat API Key Configuration

**API key must NOT be hardcoded. Use xcconfig files.**

```
# Config/Debug.xcconfig
RC_API_KEY = appl_PLACEHOLDER_SET_IN_ENV

# Config/Release.xcconfig
RC_API_KEY = appl_PLACEHOLDER_SET_IN_ENV
```

```swift
// Read from Info.plist (set via xcconfig)
guard let apiKey = Bundle.main.infoDictionary?["RC_API_KEY"] as? String else {
    fatalError("RC_API_KEY not found in Info.plist")
}
Purchases.configure(withAPIKey: apiKey)
```

Source: [RevenueCat Configuring SDK](https://www.revenuecat.com/docs/getting-started/quickstart/ios) — "Configure Purchases with your API key on app launch"

### Info.plist Required Entries

| Key | Value | Purpose |
|-----|-------|---------|
| NSHealthShareUsageDescription | "FrostDip reads your heart rate during cold plunge sessions to track your physiological response." | HealthKit read permission |
| ITSAppUsesNonExemptEncryption | NO | Export compliance |
| RC_API_KEY | $(RC_API_KEY) | RevenueCat API key from xcconfig |

---

## 2. Phase Breakdown

| Phase | Features | Files | Complexity |
|-------|----------|-------|------------|
| Phase 1: Project Setup | Infrastructure, xcconfig, PrivacyInfo | Config/, Resources/, App/ | Low |
| Phase 2: Data Layer | F-003 (Session Logging) | Models/, Services/Protocols/ | Medium |
| Phase 3: Timer Core | F-001 (Timer), F-002 (Breathing Prep) | Services/TimerService, Views/Timer/ | High |
| Phase 4: History & Streaks | F-004 (7-Day History), F-008 (Unlimited), F-010 (Streaks) | Views/History/, ViewModels/HistoryVM | Medium |
| Phase 5: HealthKit | F-007 (HR Integration) | Services/HealthKitService, TimerViewModel | High |
| Phase 6: Monetization | F-013 (Paywall), F-005 (Default Protocol), F-009 (Custom Protocols) | Services/SubscriptionService, Views/Onboarding/PaywallView | High |
| Phase 7: Dashboard & Contrast | F-011 (Progress), F-012 (Contrast Therapy) | Views/Progress/, TimerViewModel extension | Medium |
| Phase 8: Onboarding & Settings | F-006 (Onboarding), F-014 (Settings), F-015 (Notifications) | Views/Onboarding/, Views/Settings/ | Medium |
| Phase 9: Polish | Localization, DESIGN_SYSTEM tokens, a11y IDs | Resources/, Design/ | Low |

---

## 3. Phase 1: Project Setup

### 3.1 Xcode Project Creation

```
FrostDipios/
├── FrostDip.xcodeproj
├── FrostDip/
│   ├── App/
│   │   └── FrostDipApp.swift
│   ├── Config/
│   │   ├── Debug.xcconfig
│   │   └── Release.xcconfig
│   └── Resources/
│       └── PrivacyInfo.xcprivacy
├── FrostDipTests/
└── FrostDipUITests/
```

### 3.2 FrostDipApp.swift (@main)

```swift
import SwiftUI
import SwiftData
import RevenueCat

@main
struct FrostDipApp: App {
    init() {
        guard let apiKey = Bundle.main.infoDictionary?["RC_API_KEY"] as? String,
              !apiKey.isEmpty,
              !apiKey.contains("PLACEHOLDER") else {
            // Skip RC config in tests/preview
            return
        }
        Purchases.configure(withAPIKey: apiKey)
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(for: [PlungeSession.self, PlungeProtocol.self])
    }
}
```

### 3.3 PrivacyInfo.xcprivacy

Copy from ARCHITECTURE.md §11. Must be included in Xcode project target.

### 3.4 xcconfig Setup

| File | Key | Value |
|------|-----|-------|
| Debug.xcconfig | RC_API_KEY | Set via .env during build |
| Release.xcconfig | RC_API_KEY | Set via .env during build |

**Info.plist reference:** Add `RC_API_KEY = $(RC_API_KEY)` to Info.plist.

---

## 4. Phase 2-4: Core Features

### 4.1 Data Models (F-003)

**Files:** `Models/PlungeSession.swift`, `Models/PlungeProtocol.swift`, `Models/UserPreferences.swift`

Implementation per ARCHITECTURE.md §5. All models use `@Model` for SwiftData persistence.

### 4.2 Service Protocols (DI Pattern)

**Files:** `Services/Protocols/*.swift`

```swift
// Services/Protocols/TimerServiceProtocol.swift
protocol TimerServiceProtocol {
    func startTimer(duration: TimeInterval, onTick: @escaping (TimeInterval) -> Void, onComplete: @escaping () -> Void)
    func pauseTimer()
    func resumeTimer()
    func stopTimer()
    func startBreathingPrep(duration: TimeInterval, onPhaseChange: @escaping (BreathPhase) -> Void, onComplete: @escaping () -> Void)
}

enum BreathPhase {
    case inhale, hold, exhale
}
```

```swift
// Services/Protocols/HealthKitServiceProtocol.swift
protocol HealthKitServiceProtocol {
    var isAvailable: Bool { get }
    func requestAuthorization() async throws
    func startHeartRateMonitoring(onUpdate: @escaping (Double) -> Void)
    func stopHeartRateMonitoring() -> (avg: Double?, max: Double?, samples: [Double])
}
```

```swift
// Services/Protocols/SubscriptionServiceProtocol.swift
protocol SubscriptionServiceProtocol {
    var isPremium: Bool { get }
    func configure(apiKey: String)
    func fetchOfferings() async throws -> [Package]
    func purchase(package: Package) async throws -> Bool
    func restorePurchases() async throws -> Bool
    func listenForUpdates(onChange: @escaping (Bool) -> Void)
}
```

Source: [Swift Protocol-Oriented Programming](https://developer.apple.com/videos/play/wwdc2015/408/) — "Protocol-oriented programming enables testability through dependency injection"

### 4.3 Timer Implementation (F-001, F-002)

**File:** `Services/TimerService.swift`

| Component | Implementation |
|-----------|---------------|
| Countdown | `Foundation.Timer` with 1-second interval |
| Background | `BGTaskScheduler.shared.register(forTaskWithIdentifier:)` |
| Haptics | `UIImpactFeedbackGenerator(style: .heavy)` at configurable intervals |
| Breathing phases | 4-7-8 pattern: 4s inhale → 7s hold → 8s exhale (19s/cycle). Total prep time configurable (30-120s). Number of rounds = floor(totalDuration / 19). Remaining time shows countdown |
| Background notification | Schedule `UNNotificationRequest` when entering background with remaining time |

**TimerView (F-001):**

```swift
// Views/Timer/TimerView.swift
struct TimerView: View {
    @State private var viewModel: TimerViewModel

    var body: some View {
        VStack {
            CircularTimerView(progress: viewModel.progress, timeRemaining: viewModel.timeRemaining)
            // ... temperature input, protocol selection, start/pause/stop buttons
        }
        .accessibilityIdentifier("timer_view")
    }
}
```

### 4.4 History (F-004, F-008)

**File:** `ViewModels/HistoryViewModel.swift`

```swift
@Observable
class HistoryViewModel {
    private let subscriptionService: SubscriptionServiceProtocol

    var sessions: [PlungeSession] {
        if subscriptionService.isPremium {
            return allSessions  // F-008: unlimited
        } else {
            let sevenDaysAgo = Calendar.current.date(byAdding: .day, value: -7, to: Date())!
            return allSessions.filter { $0.date >= sevenDaysAgo }  // F-004: 7-day limit
        }
    }
}
```

### 4.5 Streak Tracking (F-010)

**File:** `Services/StreakService.swift` (streak calculation logic) + `ViewModels/HistoryViewModel.swift` (calls StreakService) + `Views/Components/StreakCalendarView.swift`

| Logic | Implementation |
|-------|---------------|
| Streak increment | Check if session logged today. If yes and no session yesterday, reset to 1. If yes and session yesterday, increment |
| Streak freeze | 1 per week. UserDefaults `streak_freeze_used_this_week`, reset every Monday |
| Current vs longest | Track both in UserDefaults. Update longest when current exceeds it |
| Calendar view | `LazyVGrid` with 7 columns, dots for plunge days, colored by streak status |

---

## 5. Phase 5-6: Monetization

### 5.1 RevenueCat SDK Implementation (F-013)

**File:** `Services/SubscriptionService.swift`

```swift
import RevenueCat

/// Note: Service classes (reference types) are exempt from the struct immutability rule in coding-style.md.
/// Services use mutable `@Published` / `private(set)` properties as the standard ObservableObject pattern.
final class SubscriptionService: SubscriptionServiceProtocol {
    private(set) var isPremium: Bool = false

    func configure(apiKey: String) {
        Purchases.configure(withAPIKey: apiKey)
    }

    func fetchOfferings() async throws -> [Package] {
        let offerings = try await Purchases.shared.offerings()
        guard let current = offerings.current else { return [] }
        return current.availablePackages
    }

    func purchase(package: Package) async throws -> Bool {
        let result = try await Purchases.shared.purchase(package: package)
        let isPremium = result.customerInfo.entitlements["premium"]?.isActive == true
        self.isPremium = isPremium
        return isPremium
    }

    func restorePurchases() async throws -> Bool {
        let customerInfo = try await Purchases.shared.restorePurchases()
        let isPremium = customerInfo.entitlements["premium"]?.isActive == true
        self.isPremium = isPremium
        return isPremium
    }

    func listenForUpdates(onChange: @escaping (Bool) -> Void) {
        Task {
            for await customerInfo in Purchases.shared.customerInfoStream {
                let active = customerInfo.entitlements["premium"]?.isActive == true
                self.isPremium = active
                onChange(active)
            }
        }
    }
}
```

### 5.2 Product IDs

| Product ID | Type | Price | Trial |
|------------|------|-------|-------|
| frostdip_monthly_699 | Auto-Renewable | $6.99/mo | None |
| frostdip_annual_2999 | Auto-Renewable | $29.99/yr | 3-day free trial |

### 5.3 PaywallView (F-013) — Self-Built SwiftUI (Rule 20)

**File:** `Views/Onboarding/PaywallView.swift`

```swift
struct PaywallView: View {
    @State private var viewModel: PaywallViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                // Headline
                Text("Unlock Your Full Cold Potential")
                    .font(.title.bold())
                    .accessibilityIdentifier("paywall_headline")

                // Benefits list (3-5 items)
                benefitsList

                // Pricing cards (monthly + annual with "Save 64%" badge)
                pricingCards

                // CTA button
                Button("Start My Cold Journey") {
                    Task { await viewModel.purchase() }
                }
                .accessibilityIdentifier("paywall_cta")

                // Maybe Later button (REQUIRED — Rule 20)
                Button("Maybe Later") {
                    dismiss()
                }
                .accessibilityIdentifier("paywall_maybe_later")

                // Legal links
                HStack {
                    Link("Privacy Policy", destination: privacyPolicyURL)
                    Link("Terms of Use", destination: termsURL)
                }

                // Restore purchases
                Button("Restore Purchases") {
                    Task { await viewModel.restore() }
                }
                .accessibilityIdentifier("paywall_restore")
            }
        }
        .accessibilityIdentifier("paywall_view")
    }
}
```

**Paywall Elements Checklist (from PRD §8):**

| Element | Implementation |
|---------|---------------|
| Clear headline reflecting value | "Unlock Your Full Cold Potential" |
| 3-5 benefit bullet points | HealthKit HR, Custom Protocols, Unlimited History, Streaks, Contrast Therapy |
| Pricing grid with "Save 64%" | Monthly $6.99 + Annual $29.99 with discount badge |
| Benefit-driven CTA | "Start My Cold Journey" |
| [Maybe Later] button | REQUIRED — dismisses paywall |
| Privacy Policy + Terms links | Links to deployed URLs |
| Restore purchases | Button at bottom |

### 5.4 HealthKit Integration (F-007)

**File:** `Services/HealthKitService.swift`

```swift
import HealthKit

final class HealthKitService: HealthKitServiceProtocol {
    private let healthStore = HKHealthStore()
    private var heartRateQuery: HKAnchoredObjectQuery?
    private var samples: [Double] = []

    var isAvailable: Bool {
        HKHealthStore.isHealthDataAvailable()
    }

    func requestAuthorization() async throws {
        let heartRateType = HKQuantityType(.heartRate)
        try await healthStore.requestAuthorization(toShare: [], read: [heartRateType])
    }

    func startHeartRateMonitoring(onUpdate: @escaping (Double) -> Void) {
        let heartRateType = HKQuantityType(.heartRate)
        let query = HKAnchoredObjectQuery(
            type: heartRateType,
            predicate: HKQuery.predicateForSamples(withStart: Date(), end: nil),
            anchor: nil,
            limit: HKObjectQueryNoLimit
        ) { [weak self] _, samples, _, _, _ in
            self?.processSamples(samples, onUpdate: onUpdate)
        }
        query.updateHandler = { [weak self] _, samples, _, _, _ in
            self?.processSamples(samples, onUpdate: onUpdate)
        }
        healthStore.execute(query)
        heartRateQuery = query
    }

    func stopHeartRateMonitoring() -> (avg: Double?, max: Double?, samples: [Double]) {
        if let query = heartRateQuery {
            healthStore.stop(query)
            heartRateQuery = nil
        }
        guard !samples.isEmpty else { return (nil, nil, []) }
        let avg = samples.reduce(0, +) / Double(samples.count)
        let max = samples.max()
        let result = (avg: Optional(avg), max: max, samples: samples)
        samples = []
        return result
    }

    private func processSamples(_ newSamples: [HKSample]?, onUpdate: @escaping (Double) -> Void) {
        guard let heartRateSamples = newSamples as? [HKQuantitySample] else { return }
        for sample in heartRateSamples {
            let bpm = sample.quantity.doubleValue(for: HKUnit.count().unitDivided(by: .minute()))
            samples.append(bpm)
            DispatchQueue.main.async { onUpdate(bpm) }
        }
    }
}
```

Source: [Apple HealthKit Heart Rate](https://developer.apple.com/documentation/healthkit/hkquantitytype/3583089-heartrate) — "Read heart rate samples using anchored object queries"

---

## 6. Phase 7-8: Polish

### 6.1 Progress Dashboard (F-011)

**File:** `Views/Progress/ProgressDashboardView.swift`, `ViewModels/ProgressViewModel.swift`

| Chart | Data Source | Library |
|-------|-----------|---------|
| Duration over time | PlungeSession.duration grouped by week | Swift Charts |
| Avg HR trend | PlungeSession.heartRateAvg grouped by week | Swift Charts |
| Temperature trend | PlungeSession.waterTemperature grouped by week | Swift Charts |
| Total sessions | Count of PlungeSession | Text display |
| Total cold time | Sum of PlungeSession.duration | Text display |

Source: [Apple Swift Charts](https://developer.apple.com/documentation/charts) — "Available in iOS 16.0+, creates informative, delightful visualizations"

### 6.2 Contrast Therapy Mode (F-012)

**File:** Extended `TimerViewModel` with contrast mode

| Phase | Duration | Haptic |
|-------|----------|--------|
| Hot phase | User-configured (default 3min) | Single tap at start |
| Cold phase | User-configured (default 2min) | Double tap at start |
| Rest between | User-configured (default 30s) | Light tap |
| Repeat | User-configured rounds (default 3) | — |

### 6.3 Onboarding Flow (F-006)

**File:** `Views/Onboarding/OnboardingView.swift`

| Step | Screen | Action |
|------|--------|--------|
| 1 | Welcome | App intro + cold plunge benefits |
| 2 | Experience Level | Select beginner/intermediate/advanced |
| 3 | Notifications | Request notification permission |
| 4 | Paywall | Soft paywall with [Maybe Later] (Rule 20) |

### 6.4 Settings (F-014)

**File:** `Views/Settings/SettingsView.swift`

| Section | Items |
|---------|-------|
| Preferences | Temperature unit (C/F toggle), Notification time |
| Subscription | "Upgrade to Premium" (if free) / "Premium Active" (if subscribed), Restore Purchases |
| About | Version, Privacy Policy link, Terms link |

### 6.5 Local Notifications (F-015)

**File:** `Services/NotificationService.swift`

```swift
import UserNotifications

final class NotificationService: NotificationServiceProtocol {
    func requestPermission() async throws -> Bool {
        let center = UNUserNotificationCenter.current()
        let granted = try await center.requestAuthorization(options: [.alert, .sound, .badge])
        return granted
    }

    func scheduleReminder(at time: DateComponents, title: String, body: String) {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default

        let trigger = UNCalendarNotificationTrigger(dateMatching: time, repeats: true)
        let request = UNNotificationRequest(identifier: "daily_reminder", content: content, trigger: trigger)
        UNUserNotificationCenter.current().add(request)
    }

    func scheduleStreakWarning() {
        let content = UNMutableNotificationContent()
        content.title = "Streak at Risk!"
        content.body = "Don't break your streak! Time for a cold plunge."
        content.sound = .default

        var dateComponents = DateComponents()
        dateComponents.hour = 20  // 8pm
        dateComponents.minute = 0

        let trigger = UNCalendarNotificationTrigger(dateMatching: dateComponents, repeats: true)
        let request = UNNotificationRequest(identifier: "streak_warning", content: content, trigger: trigger)
        UNUserNotificationCenter.current().add(request)
    }

    func cancelAll() {
        UNUserNotificationCenter.current().removeAllPendingNotificationRequests()
    }
}
```

---

## 7. Phase 9: Testing & Release Prep

### 7.1 Unit Tests (30+ tests)

| Test Group | Target | Tests |
|-----------|--------|-------|
| PlungeSession | Model | init, properties, defaults, temperature conversion |
| PlungeProtocol | Model | init, default protocol, custom protocol |
| UserPreferences | Model | temperature unit toggle, experience level |
| TimerService | Service | start, pause, resume, stop, breathing prep phases |
| HealthKitService | Service | availability check, authorization, HR monitoring mock |
| SubscriptionService | Service | premium check, offering fetch, purchase flow |
| NotificationService | Service | permission request, schedule, cancel |
| TimerViewModel | ViewModel | timer state transitions, session creation, HR integration |
| HistoryViewModel | ViewModel | 7-day filter (free), unlimited (premium), sort order |
| ProgressViewModel | ViewModel | chart data aggregation, empty state |
| PaywallViewModel | ViewModel | offering display, purchase result, restore |
| StreakCalculation | Logic | increment, reset, freeze, current vs longest |

### 7.2 Integration Tests

| Test | What It Verifies |
|------|-----------------|
| Timer → Session | Timer completion creates PlungeSession in SwiftData |
| Timer → HealthKit | HR samples saved to session on completion |
| Subscription → Feature Gate | Premium entitlement unlocks correct features |
| Onboarding → Paywall | Onboarding final step shows PaywallView |

### 7.3 Greenlight Checks

```bash
# Rule 17: No analytics SDK
grep -rE "Mixpanel|Analytics|Firebase" FrostDip/ --include="*.swift" | grep -v "Tests/" | wc -l
# Expected: 0

# Rule 20: No RevenueCatUI
grep -r "RevenueCatUI" FrostDip/ --include="*.swift" | wc -l
# Expected: 0

# Rule 20b: No ATT
grep -r "ATTrackingManager\|requestTrackingAuthorization" FrostDip/ --include="*.swift" | wc -l
# Expected: 0

# Rule 21: No AI APIs
grep -rE "OpenAI|Anthropic|GoogleGenerativeAI|FoundationModels" FrostDip/ --include="*.swift" | wc -l
# Expected: 0
```

---

## 8. Build & Run

### fastlane Lanes

| Task | Command |
|------|---------|
| Run tests | `cd FrostDipios && fastlane test` |
| Build (debug) | `cd FrostDipios && fastlane build` |
| Archive + upload | `cd FrostDipios && fastlane release` |

### Fastfile Configuration

```ruby
default_platform(:ios)

platform :ios do
  desc "Run all tests"
  lane :test do
    run_tests(
      scheme: "FrostDip",
      devices: ["iPhone 15 Pro"],
      clean: true
    )
  end

  desc "Build for testing"
  lane :build do
    build_app(
      scheme: "FrostDip",
      skip_archive: true,
      skip_codesigning: true
    )
  end

  desc "Archive and upload to ASC"
  lane :release do
    build_app(
      scheme: "FrostDip",
      export_method: "app-store"
    )
    upload_to_app_store(
      skip_screenshots: true,
      skip_metadata: true
    )
  end
end
```

### Development Workflow

```
1. fastlane test          # RED: write failing test
2. Implement feature      # GREEN: make test pass
3. fastlane test          # Verify GREEN
4. Refactor               # REFACTOR: clean up
5. fastlane test          # Confirm still GREEN
6. fastlane build         # Verify compilation
7. git commit             # Commit changes
```

Source: [fastlane Documentation](https://docs.fastlane.tools/) — "fastlane handles tedious tasks like generating screenshots, dealing with code signing, and releasing your application"
