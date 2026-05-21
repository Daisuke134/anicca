# Technical Architecture: AffirmFlow

**Version:** 1.0.0
**Date:** 2026-03-01
**Status:** APPROVED

---

## 1. Architecture Overview

AffirmFlow uses **MVVM (Model-View-ViewModel)** architecture with a privacy-first, on-device design.

```
┌─────────────────────────────────────────────────────────────────┐
│                        ARCHITECTURE DIAGRAM                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    PRESENTATION LAYER                   │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │    │
│  │  │  HomeView   │  │ SettingsView│  │ FavoritesView│     │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │              WidgetExtension                    │    │    │
│  │  │  AffirmationWidget (Small, Medium, Large)       │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    VIEWMODEL LAYER                       │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │    │
│  │  │HomeViewModel│  │SettingsVM  │  │FavoritesVM  │      │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                     SERVICE LAYER                        │    │
│  │  ┌─────────────────┐  ┌─────────────────┐               │    │
│  │  │AffirmationService│  │SubscriptionService│            │    │
│  │  └─────────────────┘  └─────────────────┘               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                       DATA LAYER                         │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │    │
│  │  │ SwiftData   │  │ UserDefaults│  │Foundation   │      │    │
│  │  │ (History)   │  │ (Settings) │  │ Models      │      │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

| Layer | Technology | Version | Rationale |
|-------|------------|---------|-----------|
| **UI Framework** | SwiftUI | iOS 26 | Modern, declarative, widget support |
| **AI Framework** | Foundation Models | iOS 26 | On-device AI, privacy-first |
| **Widget** | WidgetKit | iOS 26 | Native widget support |
| **Persistence** | SwiftData | iOS 17+ | Modern, type-safe persistence |
| **Settings** | UserDefaults | - | Simple key-value storage |
| **Subscriptions** | RevenueCat | 5.x | In-app purchase management |
| **Architecture** | MVVM | - | Separation of concerns |

---

## 3. Module Structure

### 3.1 Project Structure

```
AffirmFlowios/
├── App/
│   ├── AffirmFlowApp.swift           # App entry point
│   └── AppDelegate.swift             # App lifecycle
├── Models/
│   ├── Affirmation.swift             # SwiftData model
│   ├── FocusArea.swift               # Focus area enum
│   └── UserSettings.swift            # Settings model
├── ViewModels/
│   ├── HomeViewModel.swift           # Home screen logic
│   ├── OnboardingViewModel.swift     # Onboarding flow
│   ├── SettingsViewModel.swift       # Settings logic
│   └── FavoritesViewModel.swift      # Favorites logic
├── Views/
│   ├── Home/
│   │   ├── HomeView.swift            # Main app view
│   │   └── AffirmationCardView.swift # Affirmation display
│   ├── Onboarding/
│   │   ├── OnboardingView.swift      # Onboarding container
│   │   ├── WelcomeView.swift         # Welcome screen
│   │   └── FocusAreaView.swift       # Focus selection
│   ├── Settings/
│   │   ├── SettingsView.swift        # Settings screen
│   │   └── FocusAreaSettingsView.swift
│   ├── Favorites/
│   │   └── FavoritesView.swift       # Favorites list
│   ├── Paywall/
│   │   └── PaywallView.swift         # Subscription paywall
│   └── Components/
│       ├── AffirmationText.swift     # Styled text
│       └── ActionButton.swift        # Reusable button
├── Services/
│   ├── AffirmationService.swift      # AI generation
│   ├── SubscriptionService.swift     # RevenueCat wrapper
│   └── HapticsService.swift          # Haptic feedback
├── Utilities/
│   ├── AppStorageKeys.swift          # UserDefaults keys
│   └── Extensions/
│       ├── Date+Extensions.swift
│       └── View+Extensions.swift
├── Resources/
│   ├── Assets.xcassets               # Images, colors
│   ├── Localizable.strings           # Localization
│   └── PrivacyInfo.xcprivacy         # Privacy manifest
└── Widget/
    ├── AffirmationWidget.swift       # Widget entry point
    ├── AffirmationWidgetBundle.swift # Widget bundle
    ├── Provider.swift                # Timeline provider
    └── WidgetViews/
        ├── SmallWidgetView.swift
        ├── MediumWidgetView.swift
        └── LargeWidgetView.swift
```

### 3.2 Target Structure

| Target | Type | Purpose |
|--------|------|---------|
| `AffirmFlow` | App | Main application |
| `AffirmFlowWidget` | Widget Extension | Home/Lock screen widgets |
| `AffirmFlowTests` | Unit Tests | Unit test target |
| `AffirmFlowUITests` | UI Tests | UI test target |

---

## 4. Data Models

### 4.1 Affirmation Model (SwiftData)

```swift
@Model
final class Affirmation {
    @Attribute(.unique) var id: UUID
    var content: String
    var focusArea: FocusArea
    var createdAt: Date
    var isFavorite: Bool

    init(content: String, focusArea: FocusArea) {
        self.id = UUID()
        self.content = content
        self.focusArea = focusArea
        self.createdAt = Date()
        self.isFavorite = false
    }
}
```

### 4.2 FocusArea Enum

```swift
enum FocusArea: String, Codable, CaseIterable {
    case confidence = "Confidence"
    case gratitude = "Gratitude"
    case calm = "Calm"
    case motivation = "Motivation"
    case selfLove = "Self-Love"

    var systemImage: String {
        switch self {
        case .confidence: return "star.fill"
        case .gratitude: return "heart.fill"
        case .calm: return "leaf.fill"
        case .motivation: return "flame.fill"
        case .selfLove: return "person.fill"
        }
    }

    var prompt: String {
        switch self {
        case .confidence:
            return "Generate an affirmation about self-confidence and believing in abilities"
        case .gratitude:
            return "Generate an affirmation about gratitude and appreciation"
        case .calm:
            return "Generate an affirmation about inner peace and calmness"
        case .motivation:
            return "Generate an affirmation about motivation and drive"
        case .selfLove:
            return "Generate an affirmation about self-love and self-acceptance"
        }
    }
}
```

### 4.3 UserSettings

```swift
class UserSettings: ObservableObject {
    @AppStorage("selectedFocusAreas") var selectedFocusAreas: [FocusArea] = []
    @AppStorage("onboardingComplete") var onboardingComplete: Bool = false
    @AppStorage("dailyRefreshCount") var dailyRefreshCount: Int = 0
    @AppStorage("lastRefreshDate") var lastRefreshDate: Date = .distantPast

    func resetDailyCountIfNeeded() {
        if !Calendar.current.isDateInToday(lastRefreshDate) {
            dailyRefreshCount = 0
            lastRefreshDate = Date()
        }
    }
}
```

---

## 5. Services

### 5.1 AffirmationService

```swift
@Observable
class AffirmationService {
    private let session: LanguageModelSession

    init() {
        self.session = LanguageModelSession()
    }

    func generateAffirmation(for focusArea: FocusArea) async throws -> String {
        let prompt = """
        Generate a single, short affirmation (under 20 words) about \(focusArea.rawValue).
        The affirmation should be:
        - First person ("I am", "I have", "I can")
        - Present tense
        - Positive and uplifting
        - Unique and not a common cliche

        Return ONLY the affirmation text, no quotes or explanation.
        """

        let response = try await session.respond(to: prompt)
        return response.content.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
```

### 5.2 SubscriptionService

```swift
@Observable
class SubscriptionService {
    private(set) var isPremium: Bool = false

    init() {
        Purchases.shared.delegate = self
        Task { await checkSubscriptionStatus() }
    }

    func checkSubscriptionStatus() async {
        do {
            let customerInfo = try await Purchases.shared.customerInfo()
            isPremium = customerInfo.entitlements["premium"]?.isActive == true
        } catch {
            isPremium = false
        }
    }

    func purchase(package: Package) async throws {
        let result = try await Purchases.shared.purchase(package: package)
        isPremium = result.customerInfo.entitlements["premium"]?.isActive == true
    }

    func restorePurchases() async throws {
        let customerInfo = try await Purchases.shared.restorePurchases()
        isPremium = customerInfo.entitlements["premium"]?.isActive == true
    }
}
```

---

## 6. Widget Architecture

### 6.1 Widget Timeline

```
┌─────────────────────────────────────────────────────────────────┐
│                      WIDGET TIMELINE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Timeline Request                                               │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────┐                │
│  │            TimelineProvider                 │                │
│  │  ┌───────────────────────────────────────┐  │                │
│  │  │ func getTimeline(in context:) async   │  │                │
│  │  │   1. Get current affirmation          │  │                │
│  │  │   2. Create entry with affirmation    │  │                │
│  │  │   3. Schedule next refresh (midnight) │  │                │
│  │  └───────────────────────────────────────┘  │                │
│  └─────────────────────────────────────────────┘                │
│       │                                                         │
│       ▼                                                         │
│  Widget renders with AffirmationEntry                           │
│                                                                 │
│  User taps Refresh Intent                                       │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────┐                │
│  │           RefreshIntent                     │                │
│  │  1. Check daily limit                       │                │
│  │  2. Generate new affirmation (if allowed)   │                │
│  │  3. Invalidate timeline                     │                │
│  └─────────────────────────────────────────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Widget Entry

```swift
struct AffirmationEntry: TimelineEntry {
    let date: Date
    let affirmation: String
    let focusArea: FocusArea
    let canRefresh: Bool  // false if limit reached
}
```

### 6.3 App Group for Shared Data

| Key | Purpose |
|-----|---------|
| `group.com.anicca.affirmflow` | Shared container for app + widget |
| `currentAffirmation` | Current affirmation text |
| `dailyCount` | Refresh count today |
| `isPremium` | Subscription status |

---

## 7. Data Flow

### 7.1 Affirmation Generation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                   AFFIRMATION GENERATION FLOW                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User Action: Tap Refresh                                       │
│       │                                                         │
│       ▼                                                         │
│  HomeViewModel.refreshAffirmation()                             │
│       │                                                         │
│       ├──> Check daily limit                                    │
│       │         │                                               │
│       │         ├──> Limit reached: Show paywall                │
│       │         │                                               │
│       │         └──> Within limit: Continue                     │
│       │                    │                                    │
│       │                    ▼                                    │
│       │         AffirmationService.generateAffirmation()        │
│       │                    │                                    │
│       │                    ▼                                    │
│       │         Foundation Models (on-device inference)         │
│       │                    │                                    │
│       │                    ▼                                    │
│       │         New affirmation text returned                   │
│       │                    │                                    │
│       ▼                    ▼                                    │
│  Save to SwiftData    Update Widget via App Group               │
│       │                    │                                    │
│       ▼                    ▼                                    │
│  Update UI            WidgetKit.reloadAllTimelines()            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Security & Privacy

### 8.1 Privacy Architecture

| Aspect | Implementation |
|--------|----------------|
| **AI Processing** | 100% on-device via Foundation Models |
| **Data Storage** | Local SwiftData only (no cloud sync) |
| **Network Calls** | RevenueCat only (subscription validation) |
| **Analytics** | None on affirmation content |

### 8.2 Privacy Manifest (PrivacyInfo.xcprivacy)

```xml
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
    <array>
        <dict>
            <key>NSPrivacyCollectedDataType</key>
            <string>NSPrivacyCollectedDataTypePurchaseHistory</string>
            <key>NSPrivacyCollectedDataTypeLinked</key>
            <false/>
            <key>NSPrivacyCollectedDataTypeTracking</key>
            <false/>
            <key>NSPrivacyCollectedDataTypePurposes</key>
            <array>
                <string>NSPrivacyCollectedDataTypePurposeAppFunctionality</string>
            </array>
        </dict>
    </array>
</dict>
</plist>
```

---

## 9. Error Handling

### 9.1 Error Types

```swift
enum AffirmFlowError: LocalizedError {
    case generationFailed
    case modelUnavailable
    case limitReached
    case subscriptionFailed

    var errorDescription: String? {
        switch self {
        case .generationFailed:
            return "Unable to generate affirmation. Please try again."
        case .modelUnavailable:
            return "AI model is not available on this device."
        case .limitReached:
            return "Daily limit reached. Upgrade to Premium for unlimited."
        case .subscriptionFailed:
            return "Subscription failed. Please try again."
        }
    }
}
```

### 9.2 Error Handling Strategy

| Scenario | Handling |
|----------|----------|
| Foundation Models failure | Show cached affirmation + retry button |
| Network failure (RevenueCat) | Cache premium status locally |
| SwiftData failure | Log error, fallback to in-memory |
| Widget timeout | Show placeholder affirmation |

---

## 10. Performance Considerations

### 10.1 Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| App launch | < 1.5s | Cold start to main screen |
| Affirmation generation | < 2s | Foundation Models inference |
| Widget refresh | < 3s | Background update |
| Memory (app) | < 100 MB | Peak during inference |
| Memory (widget) | < 30 MB | Widget extension limit |

### 10.2 Optimization Strategies

| Strategy | Implementation |
|----------|----------------|
| **Lazy loading** | Load history only when viewed |
| **Caching** | Cache recent affirmations in memory |
| **Background processing** | Generate next affirmation in background |
| **Widget prefetch** | Pre-generate widget content |

---

## 11. Dependencies

### 11.1 Swift Package Manager

| Package | Version | Purpose |
|---------|---------|---------|
| RevenueCat | 5.x | In-app purchases |

### 11.2 System Frameworks

| Framework | Purpose |
|-----------|---------|
| SwiftUI | UI framework |
| WidgetKit | Widget support |
| SwiftData | Local persistence |
| FoundationModels | On-device AI |
| UserNotifications | Push notifications (P2) |

---

## 12. Build Configuration

### 12.1 Schemes

| Scheme | Configuration | Use Case |
|--------|---------------|----------|
| AffirmFlow-Debug | Debug | Development |
| AffirmFlow-Release | Release | App Store |

### 12.2 Build Settings

| Setting | Value |
|---------|-------|
| Deployment Target | iOS 26.0 |
| Swift Version | 6.0 |
| App Group | group.com.anicca.affirmflow |
| Bundle ID | com.anicca.affirmflow |
| Widget Bundle ID | com.anicca.affirmflow.widget |

---

## 13. Future Considerations

### 13.1 Extensibility

| Future Feature | Architecture Support |
|----------------|---------------------|
| Additional widgets | Widget bundle ready |
| New focus areas | Enum-based, easy to extend |
| Themes | Design tokens in place |
| Notifications | UserNotifications ready |

### 13.2 Scalability

| Concern | Design Decision |
|---------|-----------------|
| Data growth | SwiftData handles efficiently |
| Feature growth | MVVM allows isolated features |
| Widget variants | Timeline provider reusable |

---

**Document End**
