# MindSnap — Implementation Guide

**RevenueCat SDK:** Real SDK required. No Mock. No RevenueCatUI. Use `Purchases.shared.purchase(package:)` directly.

---

## Phase 0: Project Setup

| Task | Command/Action |
|------|----------------|
| Create Xcode project | `MindSnapios`, SwiftUI, iOS 18+, bundle: `com.anicca.mindsnap` |
| Add RevenueCat via SPM | `github.com/RevenueCat/purchases-ios` — latest |
| Add PrivacyInfo.xcprivacy | Target: MindSnapios, NSPrivacyAccessedAPICategoryUserDefaults + CA92.1 |
| Set Info.plist | `ITSAppUsesNonExemptEncryption = NO` |
| Create App Group | `group.com.anicca.mindsnap` (for widget shared defaults) |

---

## Phase 1: Models

### CheckIn.swift
```swift
import Foundation

struct CheckIn: Codable, Identifiable {
    let id: UUID
    let date: Date
    let mood: Int          // 1-10
    let note: String       // optional, can be empty
    let aiPrompt: String   // Foundation Models generated

    init(mood: Int, note: String = "", aiPrompt: String = "") {
        self.id = UUID()
        self.date = Date()
        self.mood = mood
        self.note = note
        self.aiPrompt = aiPrompt
    }
}
```

### InsightReport.swift
```swift
struct InsightReport: Codable {
    let weekOf: Date
    let averageMood: Double
    let summary: String    // Foundation Models generated
    let patterns: [String] // e.g., "Better mood on weekends"
}
```

---

## Phase 2: Services

### CheckInService.swift
- `save(_ checkIn: CheckIn)` → append to FileManager JSON array
- `loadAll() -> [CheckIn]` → decode from FileManager
- `delete(id: UUID)` → filter and save

Storage path: `FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("checkins.json")`

### FoundationModelsService.swift
```swift
import FoundationModels

@MainActor
class FoundationModelsService {
    func generatePrompt(mood: Int, note: String) async -> String {
        let session = LanguageModelSession()
        let context = note.isEmpty ? "Mood: \(mood)/10" : "Mood: \(mood)/10. Reflection: '\(note)'"
        let prompt = "\(context). Generate one thoughtful, warm reflection question to help this person explore their feelings. Keep it under 20 words."
        do {
            let response = try await session.respond(to: prompt)
            return response.content
        } catch {
            return defaultPrompts[mood - 1]
        }
    }

    func generateWeeklyInsights(checkIns: [CheckIn]) async -> InsightReport {
        let session = LanguageModelSession()
        let avg = Double(checkIns.map(\.mood).reduce(0, +)) / Double(checkIns.count)
        let summaryPrompt = "Weekly mood data: \(checkIns.map { "Day \($0.date): \($0.mood)/10" }.joined(separator: ", ")). Write a 2-sentence warm summary of the person's week and one observed pattern."
        let summary = (try? await session.respond(to: summaryPrompt))?.content ?? "A reflective week of self-awareness."
        return InsightReport(weekOf: Date(), averageMood: avg, summary: summary, patterns: [])
    }

    private let defaultPrompts = [
        "What small thing could bring you joy today?",
        "What's one thing you can let go of today?",
        "What support do you need right now?",
        "What's weighing on your mind?",
        "What's something you're proud of lately?",
        "What brought you energy today?",
        "What are you grateful for right now?",
        "What made you smile recently?",
        "What's going really well in your life?",
        "How can you celebrate this great feeling?"
    ]
}
```

### PurchaseService.swift — RevenueCat (REAL SDK, NO MOCK)
```swift
import RevenueCat

@MainActor
class PurchaseService: ObservableObject {
    @Published var isPremium = false

    func configure() {
        // RC_PUBLIC_KEY loaded from Info.plist or hardcoded (set in US-005)
        Purchases.configure(withAPIKey: RC_PUBLIC_KEY)
        Purchases.shared.delegate = self
        checkPremiumStatus()
    }

    func checkPremiumStatus() {
        Task {
            let customerInfo = try? await Purchases.shared.customerInfo()
            isPremium = customerInfo?.entitlements["premium"]?.isActive == true
        }
    }

    func purchaseMonthly() async throws {
        let offerings = try await Purchases.shared.offerings()
        guard let package = offerings.current?.monthly else {
            throw PurchaseError.noOffering
        }
        let (_, customerInfo, _) = try await Purchases.shared.purchase(package: package)
        isPremium = customerInfo.entitlements["premium"]?.isActive == true
    }

    func purchaseAnnual() async throws {
        let offerings = try await Purchases.shared.offerings()
        guard let package = offerings.current?.annual else {
            throw PurchaseError.noOffering
        }
        let (_, customerInfo, _) = try await Purchases.shared.purchase(package: package)
        isPremium = customerInfo.entitlements["premium"]?.isActive == true
    }

    func restorePurchases() async throws {
        let customerInfo = try await Purchases.shared.restorePurchases()
        isPremium = customerInfo.entitlements["premium"]?.isActive == true
    }
}

enum PurchaseError: Error {
    case noOffering
}
```

---

## Phase 3: Views

### PaywallView — MUST have [Maybe Later]
```swift
struct PaywallView: View {
    @Environment(\.dismiss) var dismiss
    let purchaseService: PurchaseService

    var body: some View {
        VStack(spacing: 24) {
            // headline, benefits list
            // ...

            Button("$4.99/month — Start Free Trial") {
                Task { try? await purchaseService.purchaseMonthly() }
            }
            .buttonStyle(.borderedProminent)

            Button("$29.99/year — Best Value") {
                Task { try? await purchaseService.purchaseAnnual() }
            }

            // CRITICAL: Maybe Later MUST be visible, MUST dismiss
            Button("Maybe Later") { dismiss() }
                .foregroundStyle(.secondary)
                .font(.footnote)
                .padding(.bottom, 32)
        }
    }
}
```

---

## Phase 4: Widget (WidgetKit)

- Widget target: `MindSnapWidget`
- App Group: `group.com.anicca.mindsnap`
- Entry: reads today's prompt from shared UserDefaults
- Sizes: `.systemSmall`, `.systemMedium`

---

## CRITICAL Checks Before Completing

```bash
# No Mock code (excluding Tests)
grep -r 'Mock' --include='*.swift' . | grep -v 'Tests/' | grep -v '.build/' | wc -l
# Must be 0

# RevenueCat imported
grep -r 'import RevenueCat' --include='*.swift' . | wc -l
# Must be > 0

# No RevenueCatUI
grep -r 'import RevenueCatUI' --include='*.swift' . | wc -l
# Must be 0

# Build succeeds
xcodebuild -scheme MindSnap -destination 'platform=iOS Simulator,name=iPhone 16' build
```
