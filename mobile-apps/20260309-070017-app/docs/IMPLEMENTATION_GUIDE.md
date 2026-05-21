# Implementation Guide: Zone2Daily

Source: [SpecKit SDD](https://github.com/feiskyer/claude-code-settings/blob/main/skills/speckit/SKILL.md) — 「Implementation guide must reference Feature IDs from PRD for traceability.」
Source: [RevenueCat iOS Quickstart](https://docs.revenuecat.com/docs/ios) — 「Configure Purchases.shared in App entry point.」
Source: [Apple SwiftData WWDC 2023](https://developer.apple.com/videos/play/wwdc2023/10187/) — 「ModelContainer setup at app level.」

---

## 1. Prerequisites

### Required Tools

| Tool | Version | Install |
|------|---------|---------|
| Xcode | 16.0+ | Mac App Store |
| fastlane | 2.220+ | `brew install fastlane` |
| Ruby | 3.x | `rbenv install 3.2.0` |
| CocoaPods | — | 不使用（SPM のみ） |

### SPM Packages

| Package | URL | Version |
|---------|-----|---------|
| RevenueCat | https://github.com/RevenueCat/purchases-ios | 5.x |

**🔴 絶対に追加しないもの:** RC UI extension (Rule 20), tracking SDKs (Rule 17), AI SDKs (Rule 21)

### Environment Setup (RC API Key)

```bash
# .env ファイルに保管（gitignore 必須）
RC_API_KEY=<RevenueCat Public iOS API Key>

# Xcode xcconfig 経由で読み込む
# Config/Debug.xcconfig:
RC_API_KEY=$(RC_API_KEY)

# Info.plist:
# <key>RC_API_KEY</key><string>$(RC_API_KEY)</string>

# Swift 読み込み:
let apiKey = Bundle.main.infoDictionary?["RC_API_KEY"] as? String ?? ""
```

Source: [Apple Technical Note — Info.plist](https://developer.apple.com/documentation/bundleresources/information_property_list) — 「Never hardcode secrets. Use xcconfig → Info.plist → Bundle.main.infoDictionary.」

### Xcode Signing Setup

```
1. Team ID: <Your Apple Developer Team ID> (from .env: TEAM_ID)
2. Provisioning Profile: Xcode automatic signing
3. Bundle ID: com.aniccafactory.zone2daily
4. Capabilities: Push Notifications (for UNUserNotificationCenter)
```

---

## 2. Phase Breakdown

| Phase | Features (F-ID) | Files | Complexity |
|-------|---------------|-------|-----------|
| 1: Project Setup | — | Xcode project, xcconfig, PrivacyInfo | Low |
| 2: Data Layer | F-001, F-003 | Models/, Services/Zone2Calculator | Low |
| 3: Core Screens | F-003, F-004, F-005 | ViewModels/, Views/Dashboard/, Views/Workout/ | Medium |
| 4: Onboarding | F-002, F-006 | Views/Onboarding/ | Medium |
| 5: Monetization | F-008 | Services/SubscriptionService, Views/Onboarding/PaywallView | Medium |
| 6: Polish | F-007 | DesignSystem/, Views/Settings/, Localizable.xcstrings | Low |
| 7: Testing | — | Zone2DailyTests/, maestro/ | Medium |

---

## 3. Phase 1: Project Setup

### Step 1.1: Xcode Project Creation

```bash
# fastlane を使うため、まずプロジェクトを手動作成
# Xcode → File → New → Project → App
# - Product Name: Zone2Daily
# - Bundle ID: com.aniccafactory.zone2daily
# - Team: <TEAM_ID>
# - Language: Swift
# - Interface: SwiftUI
# - Storage: SwiftData (チェック)
# - Include Tests: YES
```

### Step 1.2: xcconfig Setup

```
# File: Config/Debug.xcconfig
RC_API_KEY=appl_xxxx_debug_placeholder

# File: Config/Release.xcconfig
RC_API_KEY=appl_xxxx_real_key_from_revenuecat

# Info.plist に追加:
# RC_API_KEY → $(RC_API_KEY)
```

### Step 1.3: PrivacyInfo.xcprivacy

```xml
<!-- File: Resources/PrivacyInfo.xcprivacy -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
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
    <key>NSPrivacyTrackingDomains</key>
    <array/>
    <key>NSPrivacyTracking</key>
    <false/>
</dict>
</plist>
```

### Step 1.4: Fastlane Setup

```ruby
# Fastfile
platform :ios do
  desc "Run unit tests"
  lane :test do
    run_tests(
      scheme: "Zone2Daily",
      device: "iPhone 16 Pro",
      clean: true
    )
  end

  desc "Build for App Store"
  lane :build do
    build_app(
      scheme: "Zone2Daily",
      configuration: "Release",
      export_method: "app-store"
    )
  end
end
```

---

## 4. Phase 2: Core Features

### F-001: Zone2Calculator

```swift
// File: Services/Zone2Calculator.swift
// Implements F-001: Maffetone Method
enum Zone2Calculator {
    /// Maffetone Formula: subtract age from 180
    /// Source: https://philmaffetone.com/180-formula/
    static func zone2MaxHR(age: Int) -> Int { 180 - age }
    static func zone2MinHR(age: Int) -> Int { zone2MaxHR(age: age) - 10 }
    static func zone2Range(age: Int) -> ClosedRange<Int> {
        zone2MinHR(age: age)...zone2MaxHR(age: age)
    }
}
```

### F-003: WorkoutSession Model

```swift
// File: Models/WorkoutSession.swift
import SwiftData
import Foundation

@Model final class WorkoutSession {
    var id: UUID
    var date: Date
    var durationSeconds: Int
    var zone2Seconds: Int
    var targetHR: Int
    var notes: String?

    init(date: Date = .now, durationSeconds: Int, zone2Seconds: Int, targetHR: Int) {
        self.id = UUID()
        self.date = date
        self.durationSeconds = durationSeconds
        self.zone2Seconds = zone2Seconds
        self.targetHR = targetHR
    }

    var zone2Minutes: Double { Double(zone2Seconds) / 60.0 }
}
```

### F-004: DashboardViewModel

```swift
// File: ViewModels/DashboardViewModel.swift
import SwiftData
import Foundation

@Observable final class DashboardViewModel {
    var weeklyZone2Minutes: Double = 0
    var weeklyGoalMinutes: Int = 150
    var streak: Int = 0

    func loadWeeklyData(sessions: [WorkoutSession]) {
        let calendar = Calendar.current
        let startOfWeek = calendar.dateInterval(of: .weekOfYear, for: .now)?.start ?? .now
        let thisWeek = sessions.filter { $0.date >= startOfWeek }
        weeklyZone2Minutes = thisWeek.reduce(0) { $0 + $1.zone2Minutes }
        streak = calculateStreak(sessions: sessions)
    }

    var progressFraction: Double {
        min(weeklyZone2Minutes / Double(weeklyGoalMinutes), 1.0)
    }

    private func calculateStreak(sessions: [WorkoutSession]) -> Int {
        // Count consecutive days with zone2Seconds > 0
        let calendar = Calendar.current
        var streak = 0
        var checkDate = Date.now
        let sortedByDate = sessions.sorted { $0.date > $1.date }

        for _ in 0..<365 {
            let hasSession = sortedByDate.contains { calendar.isDate($0.date, inSameDayAs: checkDate) && $0.zone2Seconds > 0 }
            if hasSession { streak += 1 } else { break }
            checkDate = calendar.date(byAdding: .day, value: -1, to: checkDate) ?? checkDate
        }
        return streak
    }
}
```

---

## 5. Phase 3: Monetization

**🔴 Rule 20: 自前 SwiftUI PaywallView 必須。RC UI framework 禁止。**
**🔴 Rule 20: [Maybe Later] ボタン必須。**

### Product ID テーブル

| Product ID | Type | Price | Trial |
|-----------|------|-------|-------|
| `zone2daily_monthly_499` | Auto-Renewable Subscription | $4.99/月 | なし |
| `zone2daily_annual_2999` | Auto-Renewable Subscription | $29.99/年 | なし |

### RevenueCat Setup (App Entry Point)

```swift
// File: App/Zone2DailyApp.swift
import SwiftUI
import SwiftData
import RevenueCat  // Rule 20: SDK only

@main struct Zone2DailyApp: App {
    init() {
        let apiKey = Bundle.main.infoDictionary?["RC_API_KEY"] as? String ?? ""
        Purchases.configure(withAPIKey: apiKey)
        #if DEBUG
        Purchases.logLevel = .debug
        #else
        Purchases.logLevel = .error
        #endif
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(for: [WorkoutSession.self, UserProfile.self])
    }
}
```

### PaywallView (自前 SwiftUI — F-008)

```swift
// File: Views/Onboarding/PaywallView.swift
import SwiftUI
import RevenueCat  // Rule 20: SDK only

struct PaywallView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var packages: [Package] = []
    @State private var selectedPackage: Package?
    @State private var isPurchasing = false
    @State private var errorMessage: String?

    let subscriptionService: SubscriptionServiceProtocol

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                // Header
                Text("Unlock Your Zone 2 Potential")
                    .font(.title.bold())
                    .multilineTextAlignment(.center)
                    .accessibilityIdentifier("paywall_headline")

                // Benefits (4-5 bullet points)
                benefitsSection

                // Pricing Grid
                if !packages.isEmpty {
                    pricingSection
                }

                // CTA
                Button("Start Training") {
                    Task { await purchaseSelected() }
                }
                .buttonStyle(.borderedProminent)
                .disabled(selectedPackage == nil || isPurchasing)
                .accessibilityIdentifier("btn_subscribe")

                // Maybe Later — Rule 20 MANDATORY
                Button("Maybe Later") { dismiss() }
                    .foregroundColor(.secondary)
                    .accessibilityIdentifier("btn_maybe_later")

                // Privacy links
                privacyLinksSection
            }
            .padding()
        }
        .task { await loadPackages() }
    }

    private var benefitsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            ForEach([
                ("Unlimited workout history", "checkmark.circle.fill"),
                ("Weekly analytics dashboard", "chart.bar.fill"),
                ("Progress toward 150 min/week", "target"),
                ("Daily streak tracking", "flame.fill"),
            ], id: \.0) { benefit, icon in
                Label(benefit, systemImage: icon)
                    .font(.body)
            }
        }
    }

    private var pricingSection: some View {
        VStack(spacing: 12) {
            ForEach(packages, id: \.identifier) { pkg in
                PricingRowView(
                    package: pkg,
                    isSelected: selectedPackage?.identifier == pkg.identifier,
                    isAnnual: pkg.packageType == .annual
                ) {
                    selectedPackage = pkg
                }
            }
        }
    }

    private var privacyLinksSection: some View {
        HStack {
            Link("Privacy Policy", destination: URL(string: "https://daisuke134.github.io/anicca-products/zone2daily/privacy-policy")!)
            Text("·")
            Link("Terms of Use", destination: URL(string: "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/")!)
        }
        .font(.caption)
        .foregroundColor(.secondary)
    }

    private func loadPackages() async {
        packages = (try? await subscriptionService.fetchOfferings()) ?? []
        selectedPackage = packages.first(where: { $0.packageType == .annual }) ?? packages.first
    }

    private func purchaseSelected() async {
        guard let pkg = selectedPackage else { return }
        isPurchasing = true
        defer { isPurchasing = false }
        do {
            _ = try await subscriptionService.purchase(package: pkg)
        } catch {
            errorMessage = "Purchase failed. Please try again."
        }
    }
}
```

Source: [RevenueCat — Purchase Package](https://docs.revenuecat.com/docs/ios#make-a-purchase) — 「Purchases.shared.purchase(package:) is the recommended API.」

---

## 6. Phase 4: Polish

### Localization (Localizable.xcstrings)

```json
// Resources/Localizable.xcstrings
{
  "sourceLanguage": "en",
  "strings": {
    "onboarding.age.title": {
      "extractionState": "manual",
      "localizations": {
        "en": { "stringUnit": { "state": "translated", "value": "How old are you?" } },
        "ja": { "stringUnit": { "state": "translated", "value": "何歳ですか？" } }
      }
    },
    "dashboard.weeklyGoal": {
      "localizations": {
        "en": { "stringUnit": { "state": "translated", "value": "Weekly Zone 2 Goal" } },
        "ja": { "stringUnit": { "state": "translated", "value": "週間ゾーン2目標" } }
      }
    },
    "paywall.headline": {
      "localizations": {
        "en": { "stringUnit": { "state": "translated", "value": "Unlock Your Zone 2 Potential" } },
        "ja": { "stringUnit": { "state": "translated", "value": "ゾーン2の可能性を解放する" } }
      }
    },
    "paywall.maybeLater": {
      "localizations": {
        "en": { "stringUnit": { "state": "translated", "value": "Maybe Later" } },
        "ja": { "stringUnit": { "state": "translated", "value": "あとで" } }
      }
    }
  },
  "version": "1.0"
}
```

### Design System Integration

```swift
// File: DesignSystem/Colors.swift
import SwiftUI

extension Color {
    // Brand tokens (DESIGN_SYSTEM.md §1 — exact token names)
    static let brandPrimary = Color("brandPrimary")         // #F97316 orange (CTA, active)
    static let brandSuccess = Color("brandSuccess")          // #22C55E green (Zone 2 in-range)
    static let brandWarning = Color("brandWarning")          // #EAB308 yellow (Zone 2 boundary)
    static let brandDanger = Color("brandDanger")            // #EF4444 red (Zone 2 exceeded)
    static let bgPrimary = Color("bgPrimary")                // #FFF / #0A0A0A
    static let bgSecondary = Color("bgSecondary")            // #F5F5F5 / #171717
    static let surfaceCard = Color("surfaceCard")            // #FFF / #1C1C1C
    static let textPrimary = Color("textPrimary")            // #0A0A0A / #FAFAFA
    static let textSecondary = Color("textSecondary")        // #525252 / #A3A3A3
}
```

### Settings Screen (F-007)

```swift
// File: Views/Settings/SettingsView.swift
// Implements F-007: Settings with Upgrade → PaywallView navigation
struct SettingsView: View {
    @Environment(\.modelContext) private var modelContext
    @Bindable var profile: UserProfile
    @State private var showPaywall = false

    var body: some View {
        Form {
            Section("Profile") {
                Stepper("Age: \(profile.age)", value: $profile.age, in: 10...100)
                    .accessibilityIdentifier("input_age_settings")
                Stepper("Weekly Goal: \(profile.weeklyGoalMinutes) min",
                        value: $profile.weeklyGoalMinutes, in: 30...600, step: 30)
                    .accessibilityIdentifier("settings_weekly_goal_stepper")
            }
            Section {
                Button("Upgrade to Premium") { showPaywall = true }
                    .accessibilityIdentifier("btn_upgrade")
            }
        }
        .navigationTitle("Settings")
        .sheet(isPresented: $showPaywall) {
            PaywallView(subscriptionService: SubscriptionService())
        }
    }
}
```

---

## 7. Phase 5: Testing & Release Prep

### Test Order

```
1. Unit Tests (fastlane test)
   - Zone2Calculator: Maffetone formula correctness
   - WorkoutSession: zone2Minutes, zone2Percentage derivations
   - DashboardViewModel: weekly sum, streak calculation
   - SubscriptionService: mock protocol tests

2. Integration Tests
   - SwiftData save/load round-trip
   - RevenueCat offering fetch (live sandbox)

3. E2E Tests (maestro test maestro/)
   - onboarding-flow.yaml
   - workout-timer-flow.yaml
   - dashboard-flow.yaml
   - payment-monthly-flow.yaml
   - payment-annual-flow.yaml
   - payment-failure-flow.yaml
```

### Greenlight Checks (Before Build)

```bash
# Rule 17: no analytics
# Check: no third-party tracking SDK (tracking_check.sh in CI)

# Rule 20: custom PaywallView only

# Rule 20b: no ATT
# tracking_transparency_check.sh verifies ATT absence

# Rule 21: no AI
# ai_sdk_check.sh verifies no AI API usage

# PrivacyInfo exists
test -f Zone2Daily/Resources/PrivacyInfo.xcprivacy && echo "PASS PrivacyInfo" || echo "FAIL PrivacyInfo missing"
```

---

## 8. Build & Run

| Task | Command | Notes |
|------|---------|-------|
| Unit Tests | `cd zone2dailyios && fastlane test` | Requires simulator |
| Build Debug | `cd zone2dailyios && fastlane build_debug` | — |
| Build Release | `cd zone2dailyios && fastlane build` | Requires signing |
| E2E Tests | `maestro test maestro/` | Requires running simulator |
| Typecheck | `xcodebuild build -scheme Zone2Daily -destination 'generic/platform=iOS Simulator'` | Build-only |

### Free Tier Enforcement

```swift
// Implement free_tier_limit: 3 workouts per 7 days
extension DashboardViewModel {
    func canLogWorkout(sessions: [WorkoutSession], isPremium: Bool) -> Bool {
        guard !isPremium else { return true }
        let sevenDaysAgo = Calendar.current.date(byAdding: .day, value: -7, to: .now) ?? .now
        let recentCount = sessions.filter { $0.date >= sevenDaysAgo }.count
        return recentCount < 3  // free_tier_limit from PRD §8
    }
}
```

Source: [Apple App Store Review Guidelines 3.1.2](https://developer.apple.com/app-store/review/guidelines/#payments) — 「Free tier must provide genuine value before prompting for subscription.」
