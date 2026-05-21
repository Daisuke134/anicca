# MindSnap — Architecture

**Pattern:** MVVM + Service Layer (no backend, local-only)

---

## Directory Structure

```
MindSnapios/
├── App/
│   ├── MindSnapApp.swift          # @main, RevenueCat.configure()
│   └── AppState.swift             # @Observable global state
├── Views/
│   ├── HomeView.swift             # Root tab / today's check-in
│   ├── CheckInView.swift          # Mood slider + note + AI prompt
│   ├── HistoryView.swift          # Past check-ins list
│   ├── InsightsView.swift         # Weekly AI summary (premium)
│   ├── PaywallView.swift          # Soft paywall, Maybe Later
│   ├── SettingsView.swift         # Notifications, export
│   └── Components/
│       ├── MoodSlider.swift
│       ├── CheckInCard.swift
│       └── PremiumBadge.swift
├── Models/
│   ├── CheckIn.swift              # Codable: id, date, mood, note, aiPrompt
│   └── InsightReport.swift        # Codable: weekOf, summary, patterns
├── Services/
│   ├── CheckInService.swift       # CRUD: save/load/delete check-ins
│   ├── FoundationModelsService.swift  # AI prompt + insights generation
│   └── PurchaseService.swift      # RevenueCat wrapper
├── Resources/
│   ├── Assets.xcassets
│   ├── Localizable.xcstrings      # en + ja
│   └── PrivacyInfo.xcprivacy
└── Widgets/
    └── MindSnapWidget.swift       # WidgetKit today prompt
```

---

## Architecture Decisions

### Storage: UserDefaults + FileManager (no CoreData)
- **Why:** Solo dev, 1-day build, no complex queries needed
- Check-ins stored as JSON array in FileManager (Documents/)
- Subscription status cached in UserDefaults

### State Management: @Observable (Swift 5.9+)
- `AppState` holds: `checkIns: [CheckIn]`, `isPremium: Bool`, `todayPrompt: String`
- No third-party state management (Combine/RxSwift prohibited for 1-day build)

### AI: Foundation Models (on-device)
```swift
// FoundationModelsService.swift
import FoundationModels

func generatePrompt(mood: Int, note: String) async -> String {
    let session = LanguageModelSession()
    let prompt = "Mood: \(mood)/10. Note: '\(note)'. Generate one thoughtful reflection question."
    let response = try? await session.respond(to: prompt)
    return response?.content ?? defaultPrompts[mood]
}
```

### Payments: RevenueCat SDK
```swift
// PurchaseService.swift
import RevenueCat

func configure() {
    Purchases.configure(withAPIKey: RC_PUBLIC_KEY)
}

func purchaseMonthly() async throws {
    let offerings = try await Purchases.shared.offerings()
    guard let package = offerings.current?.monthly else { return }
    try await Purchases.shared.purchase(package: package)
}
```

### Widget: WidgetKit
- Shows today's AI prompt as small/medium widget
- Reads from shared AppGroup UserDefaults

---

## Data Flow

```
User opens app
    ↓
HomeView loads AppState
    ↓
CheckInView: user sets mood 1-10 + optional note
    ↓
FoundationModelsService.generatePrompt() [on-device, async]
    ↓
Prompt displayed → user taps "Done"
    ↓
CheckInService.save(checkIn) → FileManager JSON
    ↓
AppState.checkIns updated
    ↓
HistoryView shows updated list
    ↓
(Week 2+) PaywallView shown if !isPremium
```

---

## Dependencies

| Dependency | Version | Source |
|-----------|---------|--------|
| RevenueCat | Latest | SPM: `github.com/RevenueCat/purchases-ios` |
| Foundation Models | iOS 18+ built-in | Apple framework |
| WidgetKit | iOS 14+ built-in | Apple framework |

**No other third-party dependencies.** (Mixpanel, Firebase, etc. prohibited)
