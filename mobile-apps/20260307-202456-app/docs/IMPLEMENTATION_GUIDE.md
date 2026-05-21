# Implementation Guide: EyeRest

## 1. Prerequisites

| Requirement | Value |
|-------------|-------|
| Xcode | 16.0+ |
| Swift | 5.9+ |
| iOS Target | 17.0 |
| CocoaPods | Not used — SPM only |
| Signing | Apple Developer Team ID via xcconfig |

### Environment Setup

```bash
# 1. Create Xcode project
# File > New > Project > iOS > App > "EyeRest"
# Bundle ID: com.aniccafactory.eyerest
# Interface: SwiftUI
# Storage: SwiftData
# Testing: XCTest

# 2. Add RevenueCat via SPM
# File > Add Package > https://github.com/RevenueCat/purchases-ios
# Version: ~> 5.0
# Product: RevenueCat (NOT RC UI module — Rule 20)

# 3. Create xcconfig files
# Config/Debug.xcconfig:   RC_API_KEY = appl_XXXXXXXX
# Config/Release.xcconfig:  RC_API_KEY = appl_XXXXXXXX
```

### RevenueCat API Key Management

| Item | Detail |
|------|--------|
| Storage | xcconfig files (Debug.xcconfig, Release.xcconfig) — NOT hardcoded in Swift |
| Access | `Bundle.main.infoDictionary?["RC_API_KEY"] as? String` |
| Gitignore | xcconfig files containing real keys MUST be in .gitignore |
| Fallback | Empty string → RevenueCat logs warning but app still functions in free tier |

Source: [RevenueCat Best Practices](https://www.revenuecat.com/docs/getting-started/configuring-sdk#configuring-the-sdk) — "Configure the SDK as early as possible in your app's lifecycle"

---

## 2. Phase Breakdown

| Phase | Features | Key Files | Complexity |
|-------|----------|-----------|------------|
| Phase 1: Project Setup | — | xcconfig, PrivacyInfo.xcprivacy, SPM | Low |
| Phase 2: Core Features | F-001, F-002, F-003, F-004, F-005 | TimerService, NotificationService, TimerView, RestView, TimerViewModel, StatsView, StatsViewModel, ExerciseListView | Medium |
| Phase 3: Monetization | F-006, F-013 | SubscriptionService, PaywallView, PaywallViewModel, OnboardingView, OnboardingViewModel | Medium |
| Phase 4: Polish | F-007, F-008, F-009, F-010, F-011, F-012 | SettingsView, SettingsViewModel, ExerciseDetailView, ExerciseViewModel, Localizable.xcstrings, DESIGN_SYSTEM tokens | High |
| Phase 5: Testing & Release | — | Unit tests, Integration tests, Maestro E2E, Greenlight | Medium |

---

## 3. Phase 1: Project Setup

### 3.1 Xcode Project Creation

```bash
# Create project via Xcode or fastlane
# Product name: EyeRest
# Organization: com.aniccafactory
# Bundle ID: com.aniccafactory.eyerest
# Interface: SwiftUI
# Storage: SwiftData
# Include Tests: Yes
```

### 3.2 xcconfig Setup

**Config/Debug.xcconfig:**
```
RC_API_KEY = appl_DEBUG_KEY_HERE
PRODUCT_BUNDLE_IDENTIFIER = com.aniccafactory.eyerest
SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG
```

**Config/Release.xcconfig:**
```
RC_API_KEY = appl_RELEASE_KEY_HERE
PRODUCT_BUNDLE_IDENTIFIER = com.aniccafactory.eyerest
```

**Info.plist entries (via xcconfig):**
```
RC_API_KEY = $(RC_API_KEY)
ITSAppUsesNonExemptEncryption = NO
```

### 3.3 SPM Dependencies

| Package | URL | Version | Product |
|---------|-----|---------|---------|
| RevenueCat | https://github.com/RevenueCat/purchases-ios | ~> 5.0 | RevenueCat |

**DO NOT add RC UI module.** Rule 20 requires custom PaywallView.

### 3.4 PrivacyInfo.xcprivacy

Add to Xcode project root. Contents defined in ARCHITECTURE.md §11.
- NSPrivacyTracking: false
- NSPrivacyAccessedAPITypes: UserDefaults (CA92.1)

### 3.5 Background Modes

Enable in Xcode > Target > Signing & Capabilities:
- Background fetch (for BGAppRefreshTaskRequest)

Register task identifier in Info.plist:
```xml
<key>BGTaskSchedulerPermittedIdentifiers</key>
<array>
    <string>com.aniccafactory.eyerest.refresh</string>
</array>
```

---

## 4. Phase 2: Core Features

### 4.1 TimerService (F-001)

```swift
// Services/TimerService.swift
import BackgroundTasks

final class TimerService: ObservableObject {
    @Published var remainingSeconds: Int = 0
    @Published var isRunning: Bool = false
    @Published var isPaused: Bool = false

    private var timer: Timer?
    private var targetFireDate: Date?
    private let backgroundTaskIdentifier = "com.aniccafactory.eyerest.refresh"
    private let notificationService: NotificationServiceProtocol

    init(notificationService: NotificationServiceProtocol = NotificationService()) {
        self.notificationService = notificationService
    }

    func startTimer(intervalMinutes: Int) {
        remainingSeconds = intervalMinutes * 60
        targetFireDate = Date().addingTimeInterval(TimeInterval(remainingSeconds))
        isRunning = true
        isPaused = false
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            self?.tick()
        }
        scheduleBackgroundRefresh(in: TimeInterval(intervalMinutes * 60))
    }

    func pauseTimer() {
        timer?.invalidate()
        timer = nil
        isPaused = true
        targetFireDate = nil
    }

    func resumeTimer() {
        guard isPaused, remainingSeconds > 0 else { return }
        isPaused = false
        targetFireDate = Date().addingTimeInterval(TimeInterval(remainingSeconds))
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            self?.tick()
        }
    }

    func stopTimer() {
        timer?.invalidate()
        timer = nil
        isRunning = false
        isPaused = false
        targetFireDate = nil
        BGTaskScheduler.shared.cancel(taskRequestWithIdentifier: backgroundTaskIdentifier)
    }

    private func tick() {
        guard remainingSeconds > 0 else {
            timer?.invalidate()
            // Fire immediately via nil trigger (timeInterval: 0 crashes)
            notificationService.fireImmediateBreakNotification()
            return
        }
        remainingSeconds -= 1
    }

    /// Called on scenePhase == .background — save state and rely on scheduled notification
    func handleBackgroundTransition() {
        guard isRunning, let targetFireDate else { return }
        timer?.invalidate()
        timer = nil
        UserDefaults.standard.set(targetFireDate.timeIntervalSince1970, forKey: "targetFireDate")
        notificationService.scheduleBreakNotification(in: targetFireDate.timeIntervalSinceNow)
    }

    /// Called on scenePhase == .active — resume from saved state
    func handleForegroundTransition() {
        guard isRunning else { return }
        let saved = UserDefaults.standard.double(forKey: "targetFireDate")
        guard saved > 0 else { return }
        let remaining = Date(timeIntervalSince1970: saved).timeIntervalSinceNow
        if remaining <= 0 {
            remainingSeconds = 0
            notificationService.fireImmediateBreakNotification()
        } else {
            remainingSeconds = Int(remaining)
            targetFireDate = Date().addingTimeInterval(remaining)
            timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
                self?.tick()
            }
        }
        UserDefaults.standard.removeObject(forKey: "targetFireDate")
    }

    func scheduleBackgroundRefresh(in seconds: TimeInterval) {
        let request = BGAppRefreshTaskRequest(identifier: backgroundTaskIdentifier)
        request.earliestBeginDate = Date(timeIntervalSinceNow: seconds)
        try? BGTaskScheduler.shared.submit(request)
    }
}
```

### 4.2 NotificationService (F-003)

```swift
// Services/NotificationService.swift
import UserNotifications

final class NotificationService: NotificationServiceProtocol {

    func requestPermission() async -> Bool {
        let center = UNUserNotificationCenter.current()
        do {
            return try await center.requestAuthorization(options: [.alert, .sound, .badge])
        } catch {
            return false
        }
    }

    func scheduleBreakNotification(in seconds: TimeInterval) {
        guard seconds > 0 else {
            fireImmediateBreakNotification()
            return
        }
        let content = makeBreakContent()
        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: seconds, repeats: false)
        let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: trigger)
        UNUserNotificationCenter.current().add(request)
    }

    /// Fire notification immediately (nil trigger = instant delivery, avoids timeInterval: 0 crash)
    func fireImmediateBreakNotification() {
        let content = makeBreakContent()
        let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
        UNUserNotificationCenter.current().add(request)
    }

    private func makeBreakContent() -> UNMutableNotificationContent {
        let content = UNMutableNotificationContent()
        content.title = NSLocalizedString("notification_title", comment: "")
        content.body = NSLocalizedString("notification_body", comment: "")
        content.sound = .default
        content.categoryIdentifier = "eyerest.break"
        return content
    }

    func cancelAllNotifications() {
        UNUserNotificationCenter.current().removeAllPendingNotificationRequests()
    }
}
```

### 4.3 TimerView + RestView (F-001, F-002)

**TimerView:** Main screen showing circular countdown timer. Displays remaining time, start/stop button, daily break count.

**RestView:** Full-screen overlay presented when timer reaches zero. Shows 20-second countdown with calming gradient animation and "Look 20 feet away" instruction. Auto-dismisses on completion and records BreakSession to SwiftData.

### 4.4 TimerViewModel

```swift
// ViewModels/TimerViewModel.swift
import SwiftUI
import SwiftData

@Observable
final class TimerViewModel {
    var remainingSeconds: Int = 0
    var isRunning: Bool = false
    var isRestActive: Bool = false
    var restRemainingSeconds: Int = 20
    var todayBreakCount: Int = 0

    private let timerService: TimerService
    private let notificationService: NotificationService

    init(timerService: TimerService = TimerService(),
         notificationService: NotificationService = .shared) {
        self.timerService = timerService
        self.notificationService = notificationService
    }

    func startTimer(intervalMinutes: Int) { /* ... */ }
    func stopTimer() { /* ... */ }
    func startRest() { /* ... */ }
    func completeRest(context: ModelContext) { /* ... */ }
}
```

---

## 5. Phase 3: Monetization

### 5.1 RevenueCat SDK Setup

```swift
// App/EyeRestApp.swift
import RevenueCat

@main
struct EyeRestApp: App {
    init() {
        if let apiKey = Bundle.main.infoDictionary?["RC_API_KEY"] as? String,
           !apiKey.isEmpty {
            Purchases.configure(withAPIKey: apiKey)
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(for: [BreakSession.self, FatigueEntry.self])
    }
}
```

### 5.2 NotificationServiceProtocol (Protocol DI)

```swift
// Protocols/NotificationServiceProtocol.swift
protocol NotificationServiceProtocol {
    func requestPermission() async -> Bool
    func scheduleBreakNotification(in seconds: TimeInterval)
    func fireImmediateBreakNotification()
    func cancelAllNotifications()
}
```

### 5.3 SubscriptionServiceProtocol (Protocol DI)

```swift
// Protocols/SubscriptionServiceProtocol.swift
import RevenueCat

protocol SubscriptionServiceProtocol {
    var isPremium: Bool { get }
    func fetchOfferings() async throws -> [Package]
    func purchase(package: Package) async throws -> (transaction: StoreTransaction?, customerInfo: CustomerInfo, userCancelled: Bool)
    func restorePurchases() async throws -> CustomerInfo
}
```

### 5.3 SubscriptionService (Real Implementation)

```swift
// Services/SubscriptionService.swift
import RevenueCat

final class SubscriptionService: ObservableObject, SubscriptionServiceProtocol {
    @Published var isPremium: Bool = false

    func fetchOfferings() async throws -> [Package] {
        let offerings = try await Purchases.shared.offerings()
        return offerings.current?.availablePackages ?? []
    }

    func purchase(package: Package) async throws -> (transaction: StoreTransaction?, customerInfo: CustomerInfo, userCancelled: Bool) {
        return try await Purchases.shared.purchase(package: package)
    }

    func restorePurchases() async throws -> CustomerInfo {
        return try await Purchases.shared.restorePurchases()
    }

    func checkEntitlement() async {
        let customerInfo = try? await Purchases.shared.customerInfo()
        isPremium = customerInfo?.entitlements["premium"]?.isActive == true
    }
}
```

### 5.4 PaywallView (Rule 20 — Self-Built SwiftUI)

```swift
// Views/PaywallView.swift
import SwiftUI
import RevenueCat

struct PaywallView: View {
    @StateObject private var viewModel = PaywallViewModel()
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 24) {
            // Header: feature list
            // Toggle: Monthly / Annual
            // Price display with trial info
            // Purchase button
            // Restore purchases link

            Button("Maybe Later") {   // Rule 20: [Maybe Later] dismissal
                dismiss()
            }
            .accessibilityIdentifier("paywall_maybe_later")
        }
    }
}
```

**PaywallView calls `Purchases.shared.purchase(package:)` — NO RC UI module import.**

### 5.5 Product Configuration

| Product ID | Type | Price | Trial |
|-----------|------|-------|-------|
| eyerest_monthly_499 | Auto-Renewable Subscription | $4.99/mo | None |
| eyerest_annual_2999 | Auto-Renewable Subscription | $29.99/yr | 3-day free trial |

| RevenueCat Item | Value |
|----------------|-------|
| Entitlement | `premium` |
| Offering | `default` |
| trial_days | 3 (annual only) |

---

## 6. Phase 4: Polish

### 6.1 Localization (en-US + ja)

Use String Catalogs (.xcstrings) for all user-facing strings. Key strings defined in PRD §14.

| Implementation | Detail |
|---------------|--------|
| Format | Xcode 15+ String Catalogs (.xcstrings) |
| Languages | en-US (primary), ja (secondary) |
| App Name | "EyeRest" (same in both locales) |
| Number Formatting | Use Locale-aware formatters |

### 6.2 Animations

| Screen | Animation | Duration | Type |
|--------|-----------|----------|------|
| RestView | Gradient pulse (calming blue-green) | 20s loop | Linear |
| TimerView | Circular progress ring | Continuous | Linear |
| PaywallView | Feature checkmark entrance | 0.3s each | Spring |
| OnboardingView | Page transition | 0.35s | EaseInOut |

### 6.3 Error Handling

All error types and handling defined in ARCHITECTURE.md §12. Key principle: silent degradation for non-critical errors, clear user messaging for purchase/permission errors.

---

## 7. Phase 5: Testing & Release Prep

### 7.1 Unit Tests (TDD — RED → GREEN → REFACTOR)

| Test File | Target | Tests |
|-----------|--------|-------|
| TimerViewModelTests | TimerViewModel | start/stop timer, tick countdown, break completion, streak calc |
| StatsViewModelTests | StatsViewModel | daily count, weekly aggregation, streak logic, fatigue chart data |
| SubscriptionServiceTests | SubscriptionService | fetch offerings, purchase flow, restore, entitlement check |
| BreakSessionTests | BreakSession | model creation, interval validation, date handling |
| FatigueEntryTests | FatigueEntry | level range (1-5), session linking |

### 7.2 Integration Tests

| Test | Services Involved |
|------|------------------|
| Timer → Notification | TimerService fires → NotificationService schedules |
| Purchase → Entitlement | SubscriptionService purchase → isPremium updated |
| Break → Stats | BreakSession saved → StatsViewModel reflects new count |

### 7.3 E2E Tests (Maestro)

| Flow File | Scenario | Key Assertions |
|-----------|----------|----------------|
| onboarding.yaml | Complete 3-screen onboarding + dismiss paywall | Sees timer screen after [Maybe Later] |
| timer.yaml | Start timer, wait for break, complete rest | Break count increments |
| settings.yaml | Navigate to settings, verify all options | Settings screen loads |
| payment-monthly.yaml | Tap upgrade, select monthly | Purchase flow triggered |
| payment-annual.yaml | Tap upgrade, select annual | Purchase flow with trial |
| payment-failure.yaml | Cancel purchase | Error handled gracefully |

### 7.4 Greenlight Checks (CRITICAL)

Greenlight checks are run against Swift source code (not docs) to detect prohibited imports. Rules 17, 20, 20b, 23 are enforced via `greenlight preflight EyeRestios`. See CLAUDE.md for the exact grep patterns used by the external validator.

---

## 8. Build & Run

| Task | Command |
|------|---------|
| Run tests | `cd EyeRestios && fastlane test` |
| Build (debug) | `cd EyeRestios && fastlane build` |
| Archive (release) | `cd EyeRestios && fastlane archive` |
| Upload to ASC | `cd EyeRestios && fastlane upload` |
| E2E tests | `maestro test maestro/` |
| Greenlight | `greenlight preflight EyeRestios` |

### Fastfile Lanes

```ruby
default_platform(:ios)

platform :ios do
  desc "Run unit tests"
  lane :test do
    run_tests(
      scheme: "EyeRest",
      device: "iPhone 16",
      clean: true
    )
  end

  desc "Build for testing"
  lane :build do
    build_app(
      scheme: "EyeRest",
      skip_archive: true,
      skip_codesigning: true
    )
  end

  desc "Archive for App Store"
  lane :archive do
    build_app(
      scheme: "EyeRest",
      export_method: "app-store",
      output_directory: "./build"
    )
  end

  desc "Upload to App Store Connect"
  lane :upload do
    upload_to_app_store(
      skip_metadata: true,
      skip_screenshots: true,
      ipa: "./build/EyeRest.ipa"
    )
  end
end
```

Source: [Fastlane Documentation](https://docs.fastlane.tools/) — iOS build automation
Source: CLAUDE.md — "Fastlane必須: xcodebuild直接実行禁止"
