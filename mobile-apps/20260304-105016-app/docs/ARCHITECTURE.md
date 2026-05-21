# Technical Architecture: Chi Daily

**Version:** 1.0
**Date:** 2026-03-04
**Pattern:** MVVM + SwiftData
**iOS Minimum:** iOS 26

---

## 1. Architecture Pattern: MVVM

**Chosen pattern:** MVVM (Model-View-ViewModel)

**Rationale:**
- Standard iOS architecture; SwiftUI @Observable aligns perfectly
- Solo dev: no over-engineering needed (Clean Architecture would add unnecessary layers)
- SwiftData + @Observable handles state propagation natively
- Foundation Models integration is straightforward as a service

```
View (SwiftUI)
    ↕ binds to
ViewModel (@Observable)
    ↕ calls
Service (Foundation Models / HealthKit / RevenueCat)
    ↕ reads/writes
Model (SwiftData @Model)
```

---

## 2. Technology Stack

| Layer | Technology | Version | Reason |
|-------|-----------|---------|--------|
| UI | SwiftUI | iOS 26 | Native, declarative, HIG-compliant |
| State | @Observable | iOS 17+ | Modern replacement for ObservableObject |
| Persistence | SwiftData | iOS 17+ | Native ORM; replaces CoreData boilerplate |
| On-device AI | Foundation Models | iOS 26 | Private; no API key; TCM recommendations |
| Health | HealthKit | iOS 8+ | Mood + energy logging |
| Payments | RevenueCat SDK | 5.x | Industry standard subscription management |
| Localization | Localizable.strings | — | en + ja; NSLocalizedString |
| Networking | None | — | App is 100% offline-first |
| Analytics | None | — | CRITICAL: No tracking SDK allowed |

---

## 3. Folder Structure

```
ChiDailyios/
├── App/
│   ├── ChiDailyApp.swift           # @main entry point
│   ├── AppState.swift              # Global @Observable app state
│   └── ContentView.swift           # Root navigation
├── Models/
│   ├── CheckIn.swift               # SwiftData @Model
│   ├── Recommendation.swift        # Value type (not persisted)
│   └── ConstitutionType.swift      # Enum: Wood/Fire/Earth/Metal/Water
├── ViewModels/
│   ├── HomeViewModel.swift
│   ├── CheckInViewModel.swift
│   ├── HistoryViewModel.swift
│   └── OnboardingViewModel.swift
├── Views/
│   ├── Onboarding/
│   │   ├── OnboardingView.swift
│   │   ├── OnboardingScreen1.swift
│   │   ├── OnboardingScreen2.swift
│   │   └── OnboardingScreen3.swift
│   ├── Home/
│   │   └── HomeView.swift
│   ├── CheckIn/
│   │   ├── CheckInView.swift
│   │   └── QuestionCard.swift
│   ├── Result/
│   │   ├── ResultView.swift
│   │   └── RecommendationCard.swift
│   ├── History/
│   │   ├── HistoryView.swift
│   │   └── HistoryDetailView.swift
│   └── Paywall/
│       └── PaywallView.swift
├── Services/
│   ├── FoundationModelsService.swift   # Foundation Models integration
│   ├── HealthKitService.swift          # HealthKit read/write
│   └── SubscriptionService.swift      # RevenueCat wrapper
├── Resources/
│   ├── en.lproj/
│   │   └── Localizable.strings
│   ├── ja.lproj/
│   │   └── Localizable.strings
│   └── Assets.xcassets/
└── ChiDailyiosTests/
    ├── Models/
    ├── ViewModels/
    └── Services/
```

---

## 4. Data Models

### CheckIn (@Model — SwiftData)

```swift
@Model
final class CheckIn {
    var id: UUID
    var date: Date
    // 5 check-in answers (1–5 scale)
    var energyLevel: Int        // 1 = very low, 5 = excellent
    var sleepQuality: Int       // 1 = poor, 5 = excellent
    var digestionComfort: Int   // 1 = uncomfortable, 5 = great
    var emotionalState: Int     // 1 = stressed, 5 = calm
    var physicalSensation: Int  // 1 = heavy/achy, 5 = light/energized
    // Generated output
    var constitutionType: String    // Wood/Fire/Earth/Metal/Water
    var foodRecommendation: String
    var movementRecommendation: String
    var restRecommendation: String
    var createdAt: Date

    init(id: UUID = UUID(), date: Date = Date(), ...) { ... }
}
```

### ConstitutionType (Enum)

```swift
enum ConstitutionType: String, CaseIterable {
    case wood = "Wood"      // 木 — Liver/Gallbladder
    case fire = "Fire"      // 火 — Heart/Small Intestine
    case earth = "Earth"    // 土 — Spleen/Stomach
    case metal = "Metal"    // 金 — Lung/Large Intestine
    case water = "Water"    // 水 — Kidney/Bladder

    var japaneseName: String { ... }
    var icon: String { ... }        // SF Symbol name
    var color: Color { ... }        // Design system color
}
```

### Recommendation (Value Type)

```swift
struct Recommendation {
    let category: RecommendationCategory    // food / movement / rest
    let title: String
    let body: String
    let tcmReasoning: String
}

enum RecommendationCategory: String {
    case food = "食"
    case movement = "動"
    case rest = "息"
}
```

---

## 5. Services

### FoundationModelsService

```swift
// Calls Apple Foundation Models on-device LLM
// Input: CheckIn answers
// Output: ConstitutionType + 3 Recommendations
// Privacy: Zero network. All inference runs on device.
actor FoundationModelsService {
    func analyze(checkIn: CheckIn) async throws -> (ConstitutionType, [Recommendation])
}
```

**Prompt strategy:** Structured system prompt with TCM constitution mapping + user's 5 scores → JSON response with constitutionType + food/movement/rest strings.

### HealthKitService

```swift
// Writes mood (HKCategoryTypeIdentifier.mindfulSession) + energy (custom)
// Requests authorization once on first check-in completion
actor HealthKitService {
    func requestAuthorization() async -> Bool
    func logMoodAndEnergy(energy: Int, mood: Int, date: Date) async
}
```

### SubscriptionService

```swift
// RevenueCat SDK wrapper
// Entitlement: "pro"
// Offerings: monthly ($4.99) + annual ($34.99)
@Observable
final class SubscriptionService {
    var isProUser: Bool
    var freeCheckInsUsed: Int

    func configure()                        // Called at app launch: Purchases.configure(withAPIKey:)
    func fetchOfferings() async             // Loads RC offerings
    func purchase(package: Package) async throws
    func restorePurchases() async throws
    func canStartCheckIn() -> Bool          // true if pro OR freeCheckInsUsed < 3
}
```

---

## 6. Navigation

```swift
// ContentView.swift
// Uses TabView for main app navigation (after onboarding)
TabView {
    HomeView()      // Tab 1: Today's check-in + result
        .tabItem { Label("Today", systemImage: "sun.max") }
    HistoryView()   // Tab 2: Past 7 days
        .tabItem { Label("History", systemImage: "calendar") }
}

// Onboarding: full-screen sheet on first launch
// PaywallView: sheet presented when free tier exhausted
```

---

## 7. Foundation Models Integration

**Framework:** `import FoundationModels` (iOS 26, Apple-only, on-device)

**Session management:**
```swift
let session = LanguageModelSession()
// System prompt sets TCM expert persona + JSON output schema
// User message contains the 5 scores
// Response parsed as JSON → ConstitutionType + Recommendations
```

**Prompt schema:**
```
System: You are a TCM wellness advisor. Given 5 scores (1–5) for energy, sleep, digestion, emotions, and physical sensation, determine the user's dominant TCM constitution for today and provide 3 recommendations. Respond ONLY in valid JSON: {"constitution":"Wood|Fire|Earth|Metal|Water","food":"...","movement":"...","rest":"...","reasoning":"..."}
User: energy=4, sleep=2, digestion=3, emotions=4, physical=2
```

---

## 8. RevenueCat Integration

**SDK:** `RevenueCat` (SPM: `https://github.com/RevenueCat/purchases-ios`)
**Entitlement:** `pro`
**Offerings:**
- `monthly` — $4.99/month (product ID: `com.aniccafactory.chidaily.monthly`)
- `annual` — $34.99/year (product ID: `com.aniccafactory.chidaily.annual`)

**Configure at launch:**
```swift
// ChiDailyApp.swift
Purchases.configure(withAPIKey: "<RC_PUBLIC_API_KEY>")
Purchases.shared.delegate = subscriptionService
```

**CRITICAL:** PaywallView uses `Purchases.shared.purchase(package:)` directly. RevenueCatUI is prohibited per CLAUDE.md Rule #20.

---

## 9. HealthKit Data Types

| HKType | Identifier | Unit | Purpose |
|--------|-----------|------|---------|
| HKCategoryType | mindfulSession | N/A | Log completed check-in as mindful session |
| HKQuantityType | stepCount | count | Read only (future Weekly Summary) |

**Privacy manifest:** `NSHealthShareUsageDescription` + `NSHealthUpdateUsageDescription` required in Info.plist.

---

## 10. Privacy Architecture

| Principle | Implementation |
|-----------|---------------|
| No network calls | URLSession not used for any feature |
| No analytics | No Mixpanel, Firebase, Amplitude, etc. |
| On-device AI | Foundation Models — inference stays on device |
| HealthKit opt-in | Authorization requested before first write |
| RevenueCat only | RC SDK makes network calls for purchase validation only |

---

## 11. Performance Targets

| Metric | Target |
|--------|--------|
| App cold launch | < 2 seconds |
| Foundation Models response | < 3 seconds (typical 1–2 sec) |
| Check-in form completion | < 2 minutes |
| History list load | < 0.5 seconds (SwiftData local fetch) |
| Memory usage | < 100 MB |
