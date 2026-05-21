# Implementation Guide: AffirmFlow

**Version:** 1.0.0
**Date:** 2026-03-01
**Status:** APPROVED

---

## 1. Project Setup

### 1.1 Create Xcode Project

```bash
# Create project directory
mkdir AffirmFlowios
cd AffirmFlowios
```

**Xcode Settings:**

| Setting | Value |
|---------|-------|
| Product Name | AffirmFlow |
| Organization Identifier | com.anicca |
| Bundle Identifier | com.anicca.affirmflow |
| Interface | SwiftUI |
| Language | Swift |
| Storage | SwiftData |
| Include Tests | Yes |

### 1.2 Add Widget Extension

1. File → New → Target
2. Select "Widget Extension"
3. Product Name: `AffirmFlowWidget`
4. Include Configuration App Intent: Yes

### 1.3 Configure App Group

1. Select AffirmFlow target → Signing & Capabilities
2. Add "App Groups"
3. Create: `group.com.anicca.affirmflow`
4. Repeat for AffirmFlowWidget target

### 1.4 Add Dependencies (SPM)

File → Add Package Dependencies:

| Package | URL | Version |
|---------|-----|---------|
| RevenueCat | https://github.com/RevenueCat/purchases-ios | 5.x |

### 1.5 Project Structure

Create this folder structure:

```
AffirmFlowios/
├── App/
├── Models/
├── ViewModels/
├── Views/
│   ├── Home/
│   ├── Onboarding/
│   ├── Settings/
│   ├── Favorites/
│   ├── Paywall/
│   └── Components/
├── Services/
├── Utilities/
│   └── Extensions/
├── Resources/
└── Widget/
    └── WidgetViews/
```

---

## 2. Phase 1: Core Infrastructure (Week 1)

### 2.1 Design Tokens

**File: `Utilities/DesignTokens.swift`**

```swift
import SwiftUI

// MARK: - Spacing
enum Spacing {
    static let xxs: CGFloat = 4
    static let xs: CGFloat = 8
    static let sm: CGFloat = 12
    static let md: CGFloat = 16
    static let lg: CGFloat = 24
    static let xl: CGFloat = 32
    static let xxl: CGFloat = 48
    static let xxxl: CGFloat = 64
}

// MARK: - Corner Radius
enum CornerRadius {
    static let small: CGFloat = 8
    static let medium: CGFloat = 12
    static let large: CGFloat = 16
    static let xlarge: CGFloat = 24
}

// MARK: - Animation
extension Animation {
    static let bouncy = Animation.spring(response: 0.5, dampingFraction: 0.7)
    static let snappy = Animation.spring(response: 0.3, dampingFraction: 0.8)
}
```

### 2.2 Focus Area Model

**File: `Models/FocusArea.swift`**

```swift
import SwiftUI

enum FocusArea: String, Codable, CaseIterable, Identifiable {
    case confidence = "Confidence"
    case gratitude = "Gratitude"
    case calm = "Calm"
    case motivation = "Motivation"
    case selfLove = "Self-Love"

    var id: String { rawValue }

    var systemImage: String {
        switch self {
        case .confidence: return "star.fill"
        case .gratitude: return "heart.fill"
        case .calm: return "leaf.fill"
        case .motivation: return "flame.fill"
        case .selfLove: return "person.fill"
        }
    }

    var color: Color {
        switch self {
        case .confidence: return Color.yellow
        case .gratitude: return Color.pink
        case .calm: return Color.teal
        case .motivation: return Color.orange
        case .selfLove: return Color.purple
        }
    }

    var description: String {
        switch self {
        case .confidence: return "Believe in yourself"
        case .gratitude: return "Appreciate life"
        case .calm: return "Find inner peace"
        case .motivation: return "Stay driven"
        case .selfLove: return "Accept yourself"
        }
    }

    var prompt: String {
        switch self {
        case .confidence:
            return "Generate a positive affirmation about self-confidence and believing in one's abilities"
        case .gratitude:
            return "Generate a positive affirmation about gratitude and appreciation for life"
        case .calm:
            return "Generate a positive affirmation about inner peace and calmness"
        case .motivation:
            return "Generate a positive affirmation about motivation and drive to succeed"
        case .selfLove:
            return "Generate a positive affirmation about self-love and self-acceptance"
        }
    }
}
```

### 2.3 Affirmation Model (SwiftData)

**File: `Models/Affirmation.swift`**

```swift
import Foundation
import SwiftData

@Model
final class Affirmation {
    @Attribute(.unique) var id: UUID
    var content: String
    var focusAreaRaw: String
    var createdAt: Date
    var isFavorite: Bool

    var focusArea: FocusArea {
        get { FocusArea(rawValue: focusAreaRaw) ?? .calm }
        set { focusAreaRaw = newValue.rawValue }
    }

    init(content: String, focusArea: FocusArea) {
        self.id = UUID()
        self.content = content
        self.focusAreaRaw = focusArea.rawValue
        self.createdAt = Date()
        self.isFavorite = false
    }
}
```

### 2.4 User Settings

**File: `Models/UserSettings.swift`**

```swift
import Foundation
import SwiftUI

@Observable
class UserSettings {
    @AppStorage("selectedFocusAreas", store: UserDefaults(suiteName: "group.com.anicca.affirmflow"))
    var selectedFocusAreasData: Data = Data()

    @AppStorage("onboardingComplete", store: UserDefaults(suiteName: "group.com.anicca.affirmflow"))
    var onboardingComplete: Bool = false

    @AppStorage("dailyRefreshCount", store: UserDefaults(suiteName: "group.com.anicca.affirmflow"))
    var dailyRefreshCount: Int = 0

    @AppStorage("lastRefreshDate", store: UserDefaults(suiteName: "group.com.anicca.affirmflow"))
    var lastRefreshDateInterval: Double = 0

    var selectedFocusAreas: [FocusArea] {
        get {
            guard let areas = try? JSONDecoder().decode([FocusArea].self, from: selectedFocusAreasData) else {
                return []
            }
            return areas
        }
        set {
            selectedFocusAreasData = (try? JSONEncoder().encode(newValue)) ?? Data()
        }
    }

    var lastRefreshDate: Date {
        get { Date(timeIntervalSince1970: lastRefreshDateInterval) }
        set { lastRefreshDateInterval = newValue.timeIntervalSince1970 }
    }

    static let freeLimit = 3

    var canRefresh: Bool {
        resetDailyCountIfNeeded()
        // Premium users always can refresh (checked separately)
        return dailyRefreshCount < Self.freeLimit
    }

    var refreshesRemaining: Int {
        resetDailyCountIfNeeded()
        return max(0, Self.freeLimit - dailyRefreshCount)
    }

    func incrementRefreshCount() {
        resetDailyCountIfNeeded()
        dailyRefreshCount += 1
        lastRefreshDate = Date()
    }

    private func resetDailyCountIfNeeded() {
        if !Calendar.current.isDateInToday(lastRefreshDate) {
            dailyRefreshCount = 0
        }
    }
}
```

### 2.5 Affirmation Service

**File: `Services/AffirmationService.swift`**

```swift
import Foundation
import FoundationModels

@Observable
class AffirmationService {
    private var session: LanguageModelSession?

    enum AffirmationError: LocalizedError {
        case modelUnavailable
        case generationFailed

        var errorDescription: String? {
            switch self {
            case .modelUnavailable:
                return "AI model is not available on this device"
            case .generationFailed:
                return "Unable to generate affirmation"
            }
        }
    }

    func generateAffirmation(for focusArea: FocusArea) async throws -> String {
        // Initialize session if needed
        if session == nil {
            guard LanguageModelSession.isAvailable else {
                throw AffirmationError.modelUnavailable
            }
            session = LanguageModelSession()
        }

        guard let session = session else {
            throw AffirmationError.modelUnavailable
        }

        let prompt = """
        \(focusArea.prompt).

        Requirements:
        - Start with "I" (first person)
        - Use present tense
        - Keep it under 20 words
        - Make it positive and uplifting
        - Be specific, not generic

        Return ONLY the affirmation text, nothing else.
        """

        do {
            let response = try await session.respond(to: prompt)
            let content = response.content
                .trimmingCharacters(in: .whitespacesAndNewlines)
                .trimmingCharacters(in: CharacterSet(charactersIn: "\""))
            return content
        } catch {
            throw AffirmationError.generationFailed
        }
    }
}
```

### 2.6 Subscription Service

**File: `Services/SubscriptionService.swift`**

```swift
import Foundation
import RevenueCat

@Observable
class SubscriptionService {
    private(set) var isPremium: Bool = false
    private(set) var offerings: Offerings?

    static let shared = SubscriptionService()

    private init() {}

    func configure() {
        Purchases.configure(withAPIKey: "YOUR_REVENUECAT_API_KEY")
        Task { await checkSubscriptionStatus() }
    }

    func checkSubscriptionStatus() async {
        do {
            let customerInfo = try await Purchases.shared.customerInfo()
            isPremium = customerInfo.entitlements["premium"]?.isActive == true

            // Save to app group for widget
            UserDefaults(suiteName: "group.com.anicca.affirmflow")?
                .set(isPremium, forKey: "isPremium")
        } catch {
            print("Failed to check subscription: \(error)")
        }
    }

    func fetchOfferings() async {
        do {
            offerings = try await Purchases.shared.offerings()
        } catch {
            print("Failed to fetch offerings: \(error)")
        }
    }

    func purchase(package: Package) async throws {
        let result = try await Purchases.shared.purchase(package: package)
        isPremium = result.customerInfo.entitlements["premium"]?.isActive == true

        UserDefaults(suiteName: "group.com.anicca.affirmflow")?
            .set(isPremium, forKey: "isPremium")
    }

    func restorePurchases() async throws {
        let customerInfo = try await Purchases.shared.restorePurchases()
        isPremium = customerInfo.entitlements["premium"]?.isActive == true

        UserDefaults(suiteName: "group.com.anicca.affirmflow")?
            .set(isPremium, forKey: "isPremium")
    }
}
```

### 2.7 Haptics Service

**File: `Services/HapticsService.swift`**

```swift
import UIKit

enum HapticsService {
    static func selection() {
        UISelectionFeedbackGenerator().selectionChanged()
    }

    static func success() {
        UINotificationFeedbackGenerator().notificationOccurred(.success)
    }

    static func error() {
        UINotificationFeedbackGenerator().notificationOccurred(.error)
    }

    static func impact(_ style: UIImpactFeedbackGenerator.FeedbackStyle = .medium) {
        UIImpactFeedbackGenerator(style: style).impactOccurred()
    }
}
```

---

## 3. Phase 2: Views Implementation (Week 2-3)

### 3.1 App Entry Point

**File: `App/AffirmFlowApp.swift`**

```swift
import SwiftUI
import SwiftData

@main
struct AffirmFlowApp: App {
    @State private var settings = UserSettings()
    @State private var affirmationService = AffirmationService()

    init() {
        SubscriptionService.shared.configure()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(settings)
                .environment(affirmationService)
        }
        .modelContainer(for: Affirmation.self)
    }
}
```

### 3.2 Content View (Root)

**File: `Views/ContentView.swift`**

```swift
import SwiftUI

struct ContentView: View {
    @Environment(UserSettings.self) private var settings

    var body: some View {
        if settings.onboardingComplete {
            HomeView()
        } else {
            OnboardingView()
        }
    }
}
```

### 3.3 Onboarding Views

**File: `Views/Onboarding/OnboardingView.swift`**

```swift
import SwiftUI

struct OnboardingView: View {
    @State private var currentPage = 0

    var body: some View {
        TabView(selection: $currentPage) {
            WelcomeView(onContinue: { currentPage = 1 })
                .tag(0)

            FocusAreaSelectionView(onContinue: { currentPage = 2 })
                .tag(1)

            WidgetTutorialView()
                .tag(2)
        }
        .tabViewStyle(.page(indexDisplayMode: .never))
        .ignoresSafeArea()
    }
}
```

**File: `Views/Onboarding/WelcomeView.swift`**

```swift
import SwiftUI

struct WelcomeView: View {
    let onContinue: () -> Void

    var body: some View {
        VStack(spacing: Spacing.xxl) {
            Spacer()

            Image(systemName: "sparkles")
                .font(.system(size: 80))
                .foregroundStyle(.linearGradient(
                    colors: [.purple, .pink],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                ))

            VStack(spacing: Spacing.md) {
                Text("AffirmFlow")
                    .font(.largeTitle)
                    .fontWeight(.bold)

                Text("AI-powered affirmations\n100% on your device")
                    .font(.title3)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }

            HStack(spacing: Spacing.sm) {
                Image(systemName: "lock.fill")
                    .foregroundColor(.green)
                Text("Your thoughts never leave your phone")
                    .font(.subheadline)
            }
            .padding()
            .background(Color.green.opacity(0.1))
            .cornerRadius(CornerRadius.medium)

            Spacer()

            Button(action: onContinue) {
                Text("Get Started")
                    .font(.headline)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.purple)
                    .cornerRadius(CornerRadius.medium)
            }
            .padding(.horizontal, Spacing.xl)
        }
        .padding(.bottom, Spacing.xxl)
    }
}
```

**File: `Views/Onboarding/FocusAreaSelectionView.swift`**

```swift
import SwiftUI

struct FocusAreaSelectionView: View {
    @Environment(UserSettings.self) private var settings
    @State private var selectedAreas: Set<FocusArea> = []
    let onContinue: () -> Void

    var body: some View {
        VStack(spacing: Spacing.lg) {
            VStack(spacing: Spacing.sm) {
                Text("Choose Your Focus")
                    .font(.title)
                    .fontWeight(.bold)

                Text("Select up to 3 areas")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            .padding(.top, Spacing.xxl)

            ScrollView {
                VStack(spacing: Spacing.md) {
                    ForEach(FocusArea.allCases) { area in
                        FocusAreaCard(
                            area: area,
                            isSelected: selectedAreas.contains(area)
                        ) {
                            toggleSelection(area)
                        }
                    }
                }
                .padding(.horizontal, Spacing.lg)
            }

            Button(action: {
                settings.selectedFocusAreas = Array(selectedAreas)
                onContinue()
            }) {
                Text("Continue")
                    .font(.headline)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(selectedAreas.isEmpty ? Color.gray : Color.purple)
                    .cornerRadius(CornerRadius.medium)
            }
            .disabled(selectedAreas.isEmpty)
            .padding(.horizontal, Spacing.xl)
            .padding(.bottom, Spacing.xl)
        }
    }

    private func toggleSelection(_ area: FocusArea) {
        HapticsService.selection()
        if selectedAreas.contains(area) {
            selectedAreas.remove(area)
        } else if selectedAreas.count < 3 {
            selectedAreas.insert(area)
        }
    }
}

struct FocusAreaCard: View {
    let area: FocusArea
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: Spacing.md) {
                Image(systemName: area.systemImage)
                    .font(.title2)
                    .foregroundColor(area.color)
                    .frame(width: 32)

                VStack(alignment: .leading, spacing: Spacing.xxs) {
                    Text(area.rawValue)
                        .font(.headline)
                        .foregroundColor(.primary)

                    Text(area.description)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }

                Spacer()

                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.purple)
                        .font(.title2)
                }
            }
            .padding(Spacing.md)
            .background(isSelected ? Color.purple.opacity(0.1) : Color(.systemBackground))
            .cornerRadius(CornerRadius.large)
            .overlay(
                RoundedRectangle(cornerRadius: CornerRadius.large)
                    .stroke(isSelected ? Color.purple : Color.gray.opacity(0.2), lineWidth: isSelected ? 2 : 1)
            )
        }
        .buttonStyle(.plain)
    }
}
```

**File: `Views/Onboarding/WidgetTutorialView.swift`**

```swift
import SwiftUI

struct WidgetTutorialView: View {
    @Environment(UserSettings.self) private var settings

    var body: some View {
        VStack(spacing: Spacing.lg) {
            Text("Add Your Widget")
                .font(.title)
                .fontWeight(.bold)
                .padding(.top, Spacing.xxl)

            // Widget preview
            VStack(spacing: Spacing.md) {
                Text("\"You have the power to create positive change\"")
                    .font(.title3)
                    .multilineTextAlignment(.center)
                    .padding()

                HStack {
                    Image(systemName: "leaf.fill")
                        .foregroundColor(.teal)
                    Text("Calm")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .padding(Spacing.lg)
            .background(Color(.systemBackground))
            .cornerRadius(CornerRadius.large)
            .shadow(color: .black.opacity(0.1), radius: 10)
            .padding(.horizontal, Spacing.xxl)

            VStack(alignment: .leading, spacing: Spacing.md) {
                InstructionRow(number: 1, text: "Long press your home screen")
                InstructionRow(number: 2, text: "Tap the + button")
                InstructionRow(number: 3, text: "Search \"AffirmFlow\"")
                InstructionRow(number: 4, text: "Add the widget")
            }
            .padding(.horizontal, Spacing.xl)

            Spacer()

            VStack(spacing: Spacing.md) {
                Button(action: completeOnboarding) {
                    Text("Done, Let's Go!")
                        .font(.headline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.purple)
                        .cornerRadius(CornerRadius.medium)
                }

                Button(action: completeOnboarding) {
                    Text("Skip for now")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
            }
            .padding(.horizontal, Spacing.xl)
            .padding(.bottom, Spacing.xxl)
        }
    }

    private func completeOnboarding() {
        settings.onboardingComplete = true
    }
}

struct InstructionRow: View {
    let number: Int
    let text: String

    var body: some View {
        HStack(spacing: Spacing.md) {
            Text("\(number)")
                .font(.headline)
                .foregroundColor(.white)
                .frame(width: 28, height: 28)
                .background(Color.purple)
                .clipShape(Circle())

            Text(text)
                .font(.body)

            Spacer()
        }
    }
}
```

### 3.4 Home View

**File: `Views/Home/HomeView.swift`**

```swift
import SwiftUI
import SwiftData

struct HomeView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(UserSettings.self) private var settings
    @Environment(AffirmationService.self) private var affirmationService

    @Query(sort: \Affirmation.createdAt, order: .reverse)
    private var allAffirmations: [Affirmation]

    @State private var currentAffirmation: Affirmation?
    @State private var isLoading = false
    @State private var showPaywall = false
    @State private var showSettings = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            VStack(spacing: Spacing.lg) {
                Spacer()

                // Affirmation Card
                AffirmationCardView(
                    affirmation: currentAffirmation,
                    isLoading: isLoading,
                    errorMessage: errorMessage
                )

                // Action Buttons
                HStack(spacing: Spacing.xxl) {
                    ActionButton(
                        systemImage: currentAffirmation?.isFavorite == true ? "heart.fill" : "heart",
                        color: .pink,
                        action: toggleFavorite
                    )

                    ActionButton(
                        systemImage: canRefresh ? "arrow.clockwise" : "lock.fill",
                        color: canRefresh ? .purple : .gray,
                        action: refresh
                    )
                }

                Spacer()

                // Navigation
                HStack(spacing: Spacing.xxl) {
                    NavigationLink(destination: HistoryView()) {
                        VStack {
                            Image(systemName: "clock.arrow.circlepath")
                                .font(.title2)
                            Text("History")
                                .font(.caption)
                        }
                        .foregroundColor(.secondary)
                    }

                    NavigationLink(destination: FavoritesView()) {
                        VStack {
                            Image(systemName: "star.fill")
                                .font(.title2)
                            Text("Favorites")
                                .font(.caption)
                        }
                        .foregroundColor(.secondary)
                    }
                }

                // Status
                if !SubscriptionService.shared.isPremium {
                    Button(action: { showPaywall = true }) {
                        Text("\(settings.refreshesRemaining) of \(UserSettings.freeLimit) today • Upgrade")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .padding(.bottom, Spacing.md)
                }
            }
            .padding()
            .navigationTitle("")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(action: { showSettings = true }) {
                        Image(systemName: "gearshape")
                    }
                }
            }
            .sheet(isPresented: $showPaywall) {
                PaywallView()
            }
            .sheet(isPresented: $showSettings) {
                SettingsView()
            }
            .task {
                if currentAffirmation == nil {
                    await generateInitialAffirmation()
                }
            }
        }
    }

    private var canRefresh: Bool {
        SubscriptionService.shared.isPremium || settings.canRefresh
    }

    private func generateInitialAffirmation() async {
        // Use most recent if exists today
        if let recent = allAffirmations.first,
           Calendar.current.isDateInToday(recent.createdAt) {
            currentAffirmation = recent
            return
        }

        await generateNewAffirmation()
    }

    private func refresh() {
        if !canRefresh {
            showPaywall = true
            return
        }

        Task {
            await generateNewAffirmation()
            if !SubscriptionService.shared.isPremium {
                settings.incrementRefreshCount()
            }
        }
    }

    private func generateNewAffirmation() async {
        isLoading = true
        errorMessage = nil

        guard let focusArea = settings.selectedFocusAreas.randomElement() else {
            errorMessage = "Please select focus areas in Settings"
            isLoading = false
            return
        }

        do {
            let content = try await affirmationService.generateAffirmation(for: focusArea)
            let affirmation = Affirmation(content: content, focusArea: focusArea)
            modelContext.insert(affirmation)
            currentAffirmation = affirmation
            HapticsService.success()

            // Update widget
            saveForWidget(content: content, focusArea: focusArea)
        } catch {
            errorMessage = error.localizedDescription
            HapticsService.error()
        }

        isLoading = false
    }

    private func toggleFavorite() {
        guard let affirmation = currentAffirmation else { return }
        affirmation.isFavorite.toggle()
        HapticsService.selection()
    }

    private func saveForWidget(content: String, focusArea: FocusArea) {
        let defaults = UserDefaults(suiteName: "group.com.anicca.affirmflow")
        defaults?.set(content, forKey: "currentAffirmation")
        defaults?.set(focusArea.rawValue, forKey: "currentFocusArea")

        // Refresh widget
        WidgetCenter.shared.reloadAllTimelines()
    }
}

struct ActionButton: View {
    let systemImage: String
    let color: Color
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .font(.title)
                .foregroundColor(color)
                .frame(width: 60, height: 60)
                .background(color.opacity(0.1))
                .clipShape(Circle())
        }
    }
}
```

**File: `Views/Home/AffirmationCardView.swift`**

```swift
import SwiftUI

struct AffirmationCardView: View {
    let affirmation: Affirmation?
    let isLoading: Bool
    let errorMessage: String?

    var body: some View {
        VStack(spacing: Spacing.md) {
            if isLoading {
                ProgressView()
                    .scaleEffect(1.5)
                    .frame(height: 100)
            } else if let error = errorMessage {
                VStack(spacing: Spacing.sm) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.title)
                        .foregroundColor(.orange)
                    Text(error)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                }
                .frame(height: 100)
            } else if let affirmation = affirmation {
                Text(affirmation.content)
                    .font(.title)
                    .fontWeight(.semibold)
                    .multilineTextAlignment(.center)
                    .lineSpacing(4)

                HStack {
                    Image(systemName: affirmation.focusArea.systemImage)
                        .foregroundColor(affirmation.focusArea.color)
                    Text(affirmation.focusArea.rawValue)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
        .padding(Spacing.xl)
        .frame(maxWidth: .infinity)
        .background(Color(.secondarySystemBackground))
        .cornerRadius(CornerRadius.large)
        .animation(.bouncy, value: affirmation?.id)
    }
}
```

### 3.5 Additional Views

Implement remaining views following same patterns:
- `Views/Favorites/FavoritesView.swift`
- `Views/History/HistoryView.swift`
- `Views/Settings/SettingsView.swift`
- `Views/Paywall/PaywallView.swift`

---

## 4. Phase 3: Widget Implementation (Week 3)

### 4.1 Widget Entry

**File: `Widget/AffirmationEntry.swift`**

```swift
import WidgetKit

struct AffirmationEntry: TimelineEntry {
    let date: Date
    let affirmation: String
    let focusArea: FocusArea
}
```

### 4.2 Timeline Provider

**File: `Widget/Provider.swift`**

```swift
import WidgetKit

struct Provider: TimelineProvider {
    func placeholder(in context: Context) -> AffirmationEntry {
        AffirmationEntry(
            date: Date(),
            affirmation: "You have the power to create positive change",
            focusArea: .calm
        )
    }

    func getSnapshot(in context: Context, completion: @escaping (AffirmationEntry) -> Void) {
        let entry = getCurrentEntry()
        completion(entry)
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<AffirmationEntry>) -> Void) {
        let entry = getCurrentEntry()

        // Refresh at midnight
        let midnight = Calendar.current.startOfDay(for: Date().addingTimeInterval(86400))
        let timeline = Timeline(entries: [entry], policy: .after(midnight))
        completion(timeline)
    }

    private func getCurrentEntry() -> AffirmationEntry {
        let defaults = UserDefaults(suiteName: "group.com.anicca.affirmflow")
        let content = defaults?.string(forKey: "currentAffirmation") ?? "Tap to get your first affirmation"
        let areaRaw = defaults?.string(forKey: "currentFocusArea") ?? "Calm"
        let area = FocusArea(rawValue: areaRaw) ?? .calm

        return AffirmationEntry(date: Date(), affirmation: content, focusArea: area)
    }
}
```

### 4.3 Widget Views

**File: `Widget/WidgetViews/MediumWidgetView.swift`**

```swift
import SwiftUI
import WidgetKit

struct MediumWidgetView: View {
    let entry: AffirmationEntry

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            Text(entry.affirmation)
                .font(.headline)
                .lineLimit(3)

            HStack {
                Image(systemName: entry.focusArea.systemImage)
                    .foregroundColor(entry.focusArea.color)
                Text(entry.focusArea.rawValue)
                    .font(.caption)
                    .foregroundColor(.secondary)

                Spacer()

                // Refresh button via App Intent
                Button(intent: RefreshAffirmationIntent()) {
                    Image(systemName: "arrow.clockwise")
                        .foregroundColor(.purple)
                }
                .buttonStyle(.plain)
            }
        }
        .padding()
        .containerBackground(.fill.tertiary, for: .widget)
    }
}
```

### 4.4 Widget Bundle

**File: `Widget/AffirmationWidgetBundle.swift`**

```swift
import WidgetKit
import SwiftUI

@main
struct AffirmationWidgetBundle: WidgetBundle {
    var body: some Widget {
        AffirmationWidget()
    }
}

struct AffirmationWidget: Widget {
    let kind: String = "AffirmationWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: Provider()) { entry in
            MediumWidgetView(entry: entry)
        }
        .configurationDisplayName("Daily Affirmation")
        .description("Get personalized AI affirmations on your home screen")
        .supportedFamilies([.systemSmall, .systemMedium, .systemLarge])
    }
}
```

---

## 5. Phase 4: Testing (Week 4)

See `TEST_SPEC.md` for complete test implementation.

---

## 6. Phase 5: App Store Preparation (Week 5-6)

See `RELEASE_SPEC.md` for complete submission guide.

---

## 7. Build Commands

| Command | Purpose |
|---------|---------|
| `xcodebuild -scheme AffirmFlow build` | Build app |
| `xcodebuild -scheme AffirmFlow test` | Run tests |
| `xcodebuild -scheme AffirmFlow archive` | Create archive |

---

## 8. Environment Variables

| Variable | Purpose |
|----------|---------|
| `REVENUECAT_API_KEY` | RevenueCat public API key |

---

**Document End**
