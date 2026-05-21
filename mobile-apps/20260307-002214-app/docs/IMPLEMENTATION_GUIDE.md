# Implementation Guide: EyeBreakIsland

**Version:** 1.0
**Date:** 2026-03-07
**SSOT:** docs/PRD.md
**Architecture:** docs/ARCHITECTURE.md

Source: [Apple Developer: ActivityKit](https://developer.apple.com/documentation/activitykit) — "Displaying live data with Live Activities"
Source: [RevenueCat: Getting Started iOS](https://www.revenuecat.com/docs/getting-started/quickstart/ios) — "Configure the Purchases SDK"
Source: [Swift Package Manager](https://developer.apple.com/documentation/xcode/adding-package-dependencies-to-your-app) — "Add package dependencies"

---

## 1. Prerequisites

### Development Environment

| Requirement | Version |
|-------------|---------|
| macOS | 14.0+ (Sonoma) |
| Xcode | 16.0+ |
| Swift | 5.9+ |
| iOS Deployment Target | 16.1 |
| Simulator | iPhone 15 Pro (Dynamic Island) |
| Real Device | iPhone 14 Pro+ recommended for Live Activity testing |

### SPM Dependencies

| Package | URL | Version | Target |
|---------|-----|---------|--------|
| RevenueCat Purchases | `https://github.com/RevenueCat/purchases-ios.git` | ~> 5.0 | EyeBreakIsland |

**Prohibited packages:** RevenueCatUI, Mixpanel, Firebase, OpenAI, Anthropic, GoogleGenerativeAI, FoundationModels (Rules 17, 20, 21)

### Xcode Signing Setup

| Setting | Value |
|---------|-------|
| Team | Anicca Factory (via `~/.config/mobileapp-builder/.env`) |
| Bundle ID | com.aniccafactory.eyebreakisland |
| Provisioning | Automatic Signing |
| Capabilities | Push Notifications |

### RevenueCat API Key Management

```
# xcconfig/Config.xcconfig
RC_PUBLIC_KEY = $(RC_PUBLIC_KEY)
```

```
# Info.plist
<key>RC_PUBLIC_KEY</key>
<string>$(RC_PUBLIC_KEY)</string>
```

```swift
// Read at runtime — NEVER hardcode
let apiKey = Bundle.main.infoDictionary?["RC_PUBLIC_KEY"] as? String ?? ""
Purchases.configure(withAPIKey: apiKey)
```

Source: [RevenueCat: Configuring SDK](https://www.revenuecat.com/docs/getting-started/quickstart/ios#configure-the-sdk) — "Configure Purchases as early as possible in your app"

---

## 2. Phase Breakdown

| Phase | Features (F-ID) | Files | Complexity |
|-------|-----------------|-------|------------|
| **Phase 1: Project Setup** | — | Xcode project, xcconfig, SPM, PrivacyInfo | Low |
| **Phase 2: Core Timer** | F-001, F-002, F-003 | TimerService, TimerViewModel, TimerView, BreakOverlayView, LiveActivity, NotificationService | High |
| **Phase 3: Monetization** | F-005 | SubscriptionService, PaywallViewModel, PaywallView | Medium |
| **Phase 4: Onboarding + Settings** | F-004, F-006, F-007, F-008 | OnboardingViewModel, OnboardingViews, SettingsViewModel, SettingsView, ProgressDashboardView | Medium |
| **Phase 5: Polish** | F-009 | Localizable.xcstrings, Constants, Design tokens, Animations | Low |

---

## 3. Phase 1: Project Setup

### Step 1: Create Xcode Project

```bash
# Xcode → File → New → Project
# Template: iOS → App
# Product Name: EyeBreakIsland
# Organization: Anicca Factory
# Bundle ID: com.aniccafactory.eyebreakisland
# Interface: SwiftUI
# Language: Swift
# Include Tests: YES
```

### Step 2: Add Widget Extension (Live Activity)

```bash
# Xcode → File → New → Target
# Template: Widget Extension
# Product Name: EyeBreakIslandWidgetExtension
# Include Live Activity: YES
```

### Step 3: Add SPM Dependency

```bash
# Xcode → File → Add Package Dependencies
# URL: https://github.com/RevenueCat/purchases-ios.git
# Version Rule: Up to Next Major (5.0.0)
# Add to target: EyeBreakIsland
# Product: RevenueCat (NOT RevenueCatUI)
```

### Step 4: Create xcconfig

```
# xcconfig/Config.xcconfig
// RevenueCat Public API Key (set via .env, never hardcode)
RC_PUBLIC_KEY =
```

### Step 5: Add PrivacyInfo.xcprivacy

Copy from ARCHITECTURE.md §11.

### Step 6: Configure Info.plist

```xml
<key>ITSAppUsesNonExemptEncryption</key>
<false/>
<key>NSSupportsLiveActivities</key>
<true/>
<key>RC_PUBLIC_KEY</key>
<string>$(RC_PUBLIC_KEY)</string>
```

---

## 4. Phase 2: Core Features

### F-001: 20-20-20 Timer Core

**Files:** `Services/TimerService.swift`, `ViewModels/TimerViewModel.swift`, `Views/Timer/TimerView.swift`, `Views/Timer/BreakOverlayView.swift`

#### TimerService Implementation

```swift
import Foundation
import ActivityKit

final class TimerService: ObservableObject, TimerServiceProtocol {
    @Published var timerState: TimerState = .idle
    @Published var remainingSeconds: Int = 20 * 60
    @Published var breakCount: Int = 0

    private var timer: Timer?
    private var activity: Activity<EyeBreakAttributes>?
    private let workInterval: Int  // seconds (default 1200 = 20 min)
    private let breakInterval: Int // seconds (default 20)

    init(workInterval: Int = 20 * 60, breakInterval: Int = 20) {
        self.workInterval = workInterval
        self.breakInterval = breakInterval
    }

    func startSession() {
        timerState = .running
        remainingSeconds = workInterval
        startTimer()
        startLiveActivity()
    }

    func stopSession() {
        timerState = .idle
        timer?.invalidate()
        timer = nil
        endLiveActivity()
    }

    func startBreak() {
        timerState = .breaking
        remainingSeconds = breakInterval
        startTimer()
        updateLiveActivity(state: currentContentState())
    }

    func completeBreak() {
        breakCount += 1
        persistBreakCount()
        timerState = .running
        remainingSeconds = workInterval
        startTimer()
        updateLiveActivity(state: currentContentState())
    }

    private func startTimer() {
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            guard let self else { return }
            if self.remainingSeconds > 0 {
                self.remainingSeconds -= 1
                self.updateLiveActivity(state: self.currentContentState())
            } else {
                self.timer?.invalidate()
                switch self.timerState {
                case .running:
                    self.startBreak()
                case .breaking:
                    self.completeBreak()
                default:
                    break
                }
            }
        }
    }

    private func persistBreakCount() {
        UserDefaults.standard.set(breakCount, forKey: "todayBreakCount")
    }
}
```

#### TimerViewModel

```swift
import SwiftUI

@MainActor
final class TimerViewModel: ObservableObject {
    @Published var timerService: TimerService
    @Published var showBreakOverlay = false

    init(timerService: TimerService = TimerService()) {
        self.timerService = timerService
    }

    var formattedTime: String {
        let minutes = timerService.remainingSeconds / 60
        let seconds = timerService.remainingSeconds % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }

    func toggleTimer() {
        switch timerService.timerState {
        case .idle, .paused:
            timerService.startSession()
        case .running:
            timerService.stopSession()
        case .breaking:
            break // Cannot stop during break
        }
    }
}
```

### F-002: Dynamic Island Live Activity

**Files:** `LiveActivity/EyeBreakAttributes.swift`, `EyeBreakIslandWidgetExtension/EyeBreakLiveActivityView.swift`

#### ActivityAttributes

```swift
import ActivityKit

struct EyeBreakAttributes: ActivityAttributes {
    public struct ContentState: Codable, Hashable {
        var timerState: String      // "running" | "breaking"
        var remainingSeconds: Int
        var breakCount: Int
    }
    var sessionId: String
}
```

#### Live Activity View (Widget Extension)

```swift
import WidgetKit
import SwiftUI

struct EyeBreakLiveActivityView: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: EyeBreakAttributes.self) { context in
            // Lock Screen banner
            LockScreenBannerView(context: context)
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.leading) {
                    Label("Eye Break", systemImage: "eye")
                }
                DynamicIslandExpandedRegion(.trailing) {
                    Text(formatTime(context.state.remainingSeconds))
                        .font(.title2.monospacedDigit())
                }
                DynamicIslandExpandedRegion(.bottom) {
                    Text("Breaks today: \(context.state.breakCount)")
                }
            } compactLeading: {
                Image(systemName: "eye")
            } compactTrailing: {
                Text(formatTime(context.state.remainingSeconds))
                    .font(.caption.monospacedDigit())
            } minimal: {
                Image(systemName: "eye")
            }
        }
    }

    private func formatTime(_ seconds: Int) -> String {
        let m = seconds / 60
        let s = seconds % 60
        return String(format: "%d:%02d", m, s)
    }
}
```

Source: [Apple Developer: Dynamic Island](https://developer.apple.com/documentation/activitykit/displaying-live-data-with-live-activities) — "Use ActivityKit to start, update, and end Live Activities"

### F-003: Background Notifications

**Files:** `Services/NotificationService.swift`

```swift
import UserNotifications

final class NotificationService: NotificationServiceProtocol {
    func requestPermission() async -> Bool {
        do {
            return try await UNUserNotificationCenter.current()
                .requestAuthorization(options: [.alert, .sound, .badge])
        } catch {
            return false
        }
    }

    func scheduleBreakNotification(after interval: TimeInterval) {
        let content = UNMutableNotificationContent()
        content.title = String(localized: "timer.break.title")
        content.body = String(localized: "timer.break.instruction")
        content.sound = .default

        let trigger = UNTimeIntervalNotificationTrigger(
            timeInterval: interval,
            repeats: false
        )

        let request = UNNotificationRequest(
            identifier: "eyebreak-\(UUID().uuidString)",
            content: content,
            trigger: trigger
        )

        UNUserNotificationCenter.current().add(request)
    }

    func cancelAll() {
        UNUserNotificationCenter.current().removeAllPendingNotificationRequests()
    }
}
```

---

## 5. Phase 3: Monetization

### F-005: Subscription (RevenueCat)

**Files:** `Services/SubscriptionService.swift`, `ViewModels/PaywallViewModel.swift`, `Views/Onboarding/PaywallView.swift`

#### Product IDs

| Product ID | Type | Price | Trial |
|-----------|------|-------|-------|
| `com.aniccafactory.eyebreakisland.monthly` | Auto-Renewable | $4.99/month | None |
| `com.aniccafactory.eyebreakisland.annual` | Auto-Renewable | $29.99/year | 7 days |

#### SubscriptionService (Protocol + DI)

```swift
import RevenueCat

protocol SubscriptionServiceProtocol {
    var status: SubscriptionStatus { get }
    func configure(apiKey: String)
    func loadOfferings() async throws -> [Package]
    func purchase(package: Package) async throws -> Bool
    func restorePurchases() async throws -> SubscriptionStatus
    func checkStatus() async -> SubscriptionStatus
}

final class SubscriptionService: ObservableObject, SubscriptionServiceProtocol {
    @Published var status: SubscriptionStatus = .free

    func configure(apiKey: String) {
        Purchases.configure(withAPIKey: apiKey)
    }

    func loadOfferings() async throws -> [Package] {
        let offerings = try await Purchases.shared.offerings()
        return offerings.current?.availablePackages ?? []
    }

    func purchase(package: Package) async throws -> Bool {
        let result = try await Purchases.shared.purchase(package: package)
        if !result.userCancelled {
            status = .pro
            return true
        }
        return false
    }

    func restorePurchases() async throws -> SubscriptionStatus {
        let info = try await Purchases.shared.restorePurchases()
        status = info.entitlements["pro"]?.isActive == true ? .pro : .free
        return status
    }

    func checkStatus() async -> SubscriptionStatus {
        do {
            let info = try await Purchases.shared.customerInfo()
            status = info.entitlements["pro"]?.isActive == true ? .pro : .free
        } catch {
            // Use cached status on error
        }
        return status
    }
}
```

#### PaywallView (Custom SwiftUI — Rule 20)

```swift
import SwiftUI
import RevenueCat

struct PaywallView: View {
    @ObservedObject var viewModel: PaywallViewModel
    let onDismiss: () -> Void  // "Maybe Later"

    var body: some View {
        VStack(spacing: 24) {
            // Header
            Text("paywall.title")
                .font(.title.bold())

            Text("paywall.subtitle")
                .font(.body)
                .foregroundStyle(.secondary)

            // Package options
            ForEach(viewModel.packages, id: \.identifier) { package in
                PackageOptionView(
                    package: package,
                    isSelected: viewModel.selectedPackage?.identifier == package.identifier
                )
                .onTapGesture {
                    viewModel.selectedPackage = package
                }
            }

            // Purchase button
            Button {
                Task { await viewModel.purchase() }
            } label: {
                Text("paywall.subscribe")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.accentColor)
                    .foregroundStyle(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 16))
            }
            .disabled(viewModel.selectedPackage == nil || viewModel.isPurchasing)

            // Maybe Later (Rule 20: REQUIRED)
            Button("paywall.maybe_later") {
                onDismiss()
            }
            .font(.subheadline)
            .foregroundStyle(.secondary)
            .accessibilityIdentifier("paywall_maybe_later")

            // Restore
            Button("paywall.restore") {
                Task { await viewModel.restore() }
            }
            .font(.caption)
            .foregroundStyle(.tertiary)
        }
        .padding()
    }
}
```

**Key:** `Purchases.shared.purchase(package:)` — NOT RevenueCatUI.

Source: [RevenueCat: Making Purchases](https://www.revenuecat.com/docs/making-purchases/ios) — "Use purchase(package:) to initiate a purchase"

---

## 6. Phase 4: Onboarding + Settings

> F-004 (Onboarding), F-006 (Schedule), F-007 (Custom Intervals), F-008 (Statistics) implementation.
> See UX_SPEC.md §6 for onboarding flow. See ARCHITECTURE.md §6 for service interfaces.

### F-004: Onboarding Flow

**Files:** `ViewModels/OnboardingViewModel.swift`, `Views/Onboarding/OnboardingView.swift`, `Views/Onboarding/OnboardingPageView.swift`

| Page | Content | Action |
|------|---------|--------|
| 1 | Welcome — "Your Eyes Need Breaks" | Next |
| 2 | Feature intro — Dynamic Island demo | Next |
| 3 | Notification permission request | Allow → auto-advance |
| 4 | Soft Paywall (PaywallView) | Subscribe / Maybe Later |

- `@AppStorage("hasCompletedOnboarding")` flag → show once
- Page 4 = PaywallView (Rule 20: self-built, no RevenueCatUI)

### F-006: Break Schedule

**Files:** `ViewModels/SettingsViewModel.swift`, `Views/Settings/SettingsView.swift`

- Work hours: start/end `DatePicker` → `UserDefaults`
- Timer only fires during scheduled hours
- Default: 09:00–18:00

### F-007: Custom Timer Intervals (Pro)

**Files:** `ViewModels/SettingsViewModel.swift`

- Interval options: 15 / 20 / 30 minutes (Pro only, free = 20 min fixed)
- Break duration options: 15 / 20 / 30 seconds (Pro only, free = 20 sec fixed)
- Gated by `SubscriptionService.shared.isProUser`

### F-008: Break Statistics (Pro)

**Files:** `ViewModels/ProgressDashboardViewModel.swift`, `Views/ProgressDashboardView.swift`

- Daily/weekly break count from `UserDefaults` (`dailyBreakCounts` dictionary)
- Current streak tracking
- Simple bar chart (SwiftUI `Chart` — iOS 16+)
- Pro-only gate

---

## 6b. Phase 5: Polish

### F-009: Localization (en-US + ja)

**File:** `Resources/Localizable.xcstrings`

| Key | en-US | ja |
|-----|-------|----|
| `timer.start` | Start Eye Break | 目休みタイマー開始 |
| `timer.stop` | Stop | 停止 |
| `timer.break.title` | Time for a 20-second break! | 20秒間、遠くを見てください！ |
| `timer.break.instruction` | Look 20 feet away for 20 seconds | 6メートル先を20秒間見つめましょう |
| `timer.running` | Next break in | 次の休憩まで |
| `timer.breaking` | Look away now | 遠くを見て |
| `paywall.title` | Protect Your Eyes Daily | 毎日、目を守ろう |
| `paywall.subtitle` | Unlock Pro features | Pro機能をアンロック |
| `paywall.subscribe` | Subscribe | 登録する |
| `paywall.maybe_later` | Maybe Later | あとで |
| `paywall.restore` | Restore Purchases | 購入を復元 |
| `onboarding.welcome.title` | Your Eyes Need Breaks | 目に休憩を |
| `onboarding.feature.title` | Always Visible Timer | 常に見えるタイマー |
| `onboarding.notification.title` | Stay Reminded | 通知で忘れない |
| `settings.title` | Settings | 設定 |
| `settings.upgrade` | Upgrade to Pro | Proにアップグレード |
| `settings.timer_interval` | Timer Interval | タイマー間隔 |
| `settings.notifications` | Notifications | 通知 |

### Animations

| Element | Trigger | Duration | Type |
|---------|---------|----------|------|
| Break overlay appear | 20-min timer reaches 0 | 0.3s | spring |
| Break overlay dismiss | 20-sec break completes | 0.3s | easeOut |
| Timer circle progress | Every second | 1.0s | linear |
| Paywall package select | Tap | 0.2s | spring |
| Onboarding page transition | Swipe/tap | 0.4s | spring |

### Error Handling

See ARCHITECTURE.md §12.

---

## 7. Phase 5: Testing & Release Prep

### Test Pyramid

| Level | Target | Count | Coverage |
|-------|--------|-------|----------|
| Unit Tests | Services, ViewModels, Models | 30+ | 70% |
| Integration Tests | Service interactions | 5+ | 20% |
| E2E (Maestro) | Full user flows | 6+ | 10% |

### Unit Test Plan

| Test File | Tests | What It Verifies |
|-----------|-------|-----------------|
| `TimerServiceTests.swift` | startSession sets running, stopSession sets idle, break increments counter, timer counts down | F-001 timer logic |
| `NotificationServiceTests.swift` | requestPermission returns Bool, scheduleBreakNotification creates request, cancelAll clears pending | F-003 notification logic |
| `SubscriptionServiceTests.swift` | configure sets up SDK, loadOfferings returns packages, purchase updates status | F-005 subscription flow |
| `TimerViewModelTests.swift` | formattedTime correct, toggleTimer changes state | ViewModel logic |
| `OnboardingViewModelTests.swift` | page progression, completion flag set | F-004 onboarding flow |

### Greenlight Checks

```bash
# Rule 17: No analytics SDK
grep -rE "Mixpanel|Analytics|Firebase" EyeBreakIsland/ --include="*.swift" | grep -v "Tests/" && echo "FAIL" || echo "PASS"

# Rule 20: No RevenueCatUI
grep -r "RevenueCatUI" EyeBreakIsland/ --include="*.swift" && echo "FAIL" || echo "PASS"

# Rule 20b: No ATT
grep -r "ATTrackingManager" EyeBreakIsland/ --include="*.swift" && echo "FAIL" || echo "PASS"

# Rule 21: No AI API
grep -rE "OpenAI|Anthropic|GoogleGenerativeAI|FoundationModels" EyeBreakIsland/ --include="*.swift" && echo "FAIL" || echo "PASS"
```

---

## 8. Build & Run

### Fastlane Commands

| Task | Command |
|------|---------|
| Run tests | `cd EyeBreakIslandios && fastlane test` |
| Build for testing | `cd EyeBreakIslandios && fastlane build` |
| Archive for distribution | `cd EyeBreakIslandios && fastlane archive` |
| Upload to TestFlight | `cd EyeBreakIslandios && fastlane beta` |

### Manual Build (development only)

```bash
# Unlock keychain
source ~/.config/mobileapp-builder/.env
security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db

# Build (MUST use Fastlane — xcodebuild direct execution prohibited)
cd EyeBreakIsland && fastlane build
```

### App Entry Point

```swift
import SwiftUI
import RevenueCat

@main
struct EyeBreakIslandApp: App {
    init() {
        let apiKey = Bundle.main.infoDictionary?["RC_PUBLIC_KEY"] as? String ?? ""
        if !apiKey.isEmpty {
            Purchases.configure(withAPIKey: apiKey)
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
```

---

**End of Implementation Guide**
