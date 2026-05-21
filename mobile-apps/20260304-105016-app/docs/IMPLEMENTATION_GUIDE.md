# Implementation Guide: Chi Daily

**Version:** 1.0
**Date:** 2026-03-04
**SDK:** RevenueCat (real SDK, NOT mock)

---

## Phase 0: Project Setup

### 0.1 Create Xcode Project

```
Xcode → File → New → Project
Template: App
Product Name: ChiDailyios
Team: [your team]
Bundle Identifier: com.aniccafactory.chidaily
Interface: SwiftUI
Language: Swift
Include Tests: YES
Minimum Deployment: iOS 26.0
```

### 0.2 SPM Dependencies

Add via Xcode → Package Dependencies:

```
RevenueCat:
URL: https://github.com/RevenueCat/purchases-ios
Version: 5.x (Up to Next Major)
Products: RevenueCat (select this; NOT RevenueCatUI)
```

### 0.3 Capabilities

In Xcode → Signing & Capabilities:
- Add **HealthKit** capability
- Add **In-App Purchase** capability (automatic with RevenueCat)

### 0.4 Info.plist Keys

```xml
<key>NSHealthShareUsageDescription</key>
<string>Chi Daily reads your health data to improve personalized recommendations.</string>
<key>NSHealthUpdateUsageDescription</key>
<string>Chi Daily logs your daily mood and energy to Apple Health for trend tracking.</string>
```

### 0.5 Folder Structure

Create folders in Xcode (matching ARCHITECTURE.md):
```
App/  Models/  ViewModels/  Views/Onboarding/  Views/Home/
Views/CheckIn/  Views/Result/  Views/History/  Views/Paywall/
Services/  Resources/en.lproj/  Resources/ja.lproj/
```

---

## Phase 1: Core Data Models

### 1.1 CheckIn.swift

```swift
import Foundation
import SwiftData

@Model
final class CheckIn {
    var id: UUID
    var date: Date
    var energyLevel: Int         // 1–5
    var sleepQuality: Int        // 1–5
    var digestionComfort: Int    // 1–5
    var emotionalState: Int      // 1–5
    var physicalSensation: Int   // 1–5
    var constitutionType: String
    var foodRecommendation: String
    var movementRecommendation: String
    var restRecommendation: String
    var createdAt: Date

    init(
        id: UUID = UUID(),
        date: Date = Date(),
        energyLevel: Int,
        sleepQuality: Int,
        digestionComfort: Int,
        emotionalState: Int,
        physicalSensation: Int,
        constitutionType: String = "",
        foodRecommendation: String = "",
        movementRecommendation: String = "",
        restRecommendation: String = "",
        createdAt: Date = Date()
    ) {
        self.id = id
        self.date = date
        self.energyLevel = energyLevel
        self.sleepQuality = sleepQuality
        self.digestionComfort = digestionComfort
        self.emotionalState = emotionalState
        self.physicalSensation = physicalSensation
        self.constitutionType = constitutionType
        self.foodRecommendation = foodRecommendation
        self.movementRecommendation = movementRecommendation
        self.restRecommendation = restRecommendation
        self.createdAt = createdAt
    }
}
```

### 1.2 ConstitutionType.swift

```swift
import SwiftUI

enum ConstitutionType: String, CaseIterable, Codable {
    case wood = "Wood"
    case fire = "Fire"
    case earth = "Earth"
    case metal = "Metal"
    case water = "Water"

    var japaneseName: String {
        switch self {
        case .wood: return "木のタイプ"
        case .fire: return "火のタイプ"
        case .earth: return "土のタイプ"
        case .metal: return "金のタイプ"
        case .water: return "水のタイプ"
        }
    }

    var icon: String {
        switch self {
        case .wood: return "leaf.fill"
        case .fire: return "flame.fill"
        case .earth: return "mountain.2.fill"
        case .metal: return "circle.hexagongrid.fill"
        case .water: return "drop.fill"
        }
    }

    var color: Color {
        switch self {
        case .wood: return Color(hex: "#5C8A4F")
        case .fire: return Color(hex: "#C85A3C")
        case .earth: return Color(hex: "#A07840")
        case .metal: return Color(hex: "#888888")
        case .water: return Color(hex: "#4472A8")
        }
    }

    static func from(string: String) -> ConstitutionType {
        ConstitutionType(rawValue: string) ?? .earth
    }
}
```

### 1.3 Recommendation.swift

```swift
import SwiftUI

enum RecommendationCategory: String {
    case food = "食"
    case movement = "動"
    case rest = "息"

    var localizedName: String {
        switch self {
        case .food: return NSLocalizedString("Food", comment: "")
        case .movement: return NSLocalizedString("Movement", comment: "")
        case .rest: return NSLocalizedString("Rest", comment: "")
        }
    }

    var sfSymbol: String {
        switch self {
        case .food: return "fork.knife"
        case .movement: return "figure.walk"
        case .rest: return "moon.fill"
        }
    }

    var color: Color {
        switch self {
        case .food: return Color(hex: "#A07840")
        case .movement: return Color(hex: "#5C8A4F")
        case .rest: return Color(hex: "#4472A8")
        }
    }
}

struct Recommendation {
    let category: RecommendationCategory
    let body: String
}
```

### 1.4 DesignTokens.swift

```swift
import SwiftUI

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 6: (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        default: (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(.sRGB, red: Double(r)/255, green: Double(g)/255, blue: Double(b)/255, opacity: Double(a)/255)
    }

    static let brandEarth = Color(hex: "#8B7355")
    static let brandSage = Color(hex: "#7A9E7E")
    static let brandCream = Color(hex: "#F5F0E8")
    static let chiAccent = Color.brandEarth
}

enum Spacing {
    static let xs: CGFloat = 4
    static let sm: CGFloat = 8
    static let md: CGFloat = 16
    static let lg: CGFloat = 24
    static let xl: CGFloat = 32
    static let xxl: CGFloat = 48
}
```

---

## Phase 2: Services

### 2.1 SubscriptionService.swift (RevenueCat — Real SDK)

```swift
import RevenueCat
import SwiftUI

@Observable
final class SubscriptionService {
    var isProUser: Bool = false
    var freeCheckInsUsed: Int = 0
    var currentOffering: Offering?

    private let freeLimit = 3

    func configure() {
        // REAL RevenueCat SDK — not a mock
        Purchases.configure(withAPIKey: "<RC_PUBLIC_API_KEY>")
        Purchases.shared.delegate = nil  // handled via async calls
        Task { await refreshStatus() }
    }

    func refreshStatus() async {
        do {
            let customerInfo = try await Purchases.shared.customerInfo()
            isProUser = customerInfo.entitlements["pro"]?.isActive == true
        } catch {
            // Non-fatal: default to free tier
        }
        freeCheckInsUsed = UserDefaults.standard.integer(forKey: "freeCheckInsUsed")
    }

    func fetchOfferings() async {
        do {
            let offerings = try await Purchases.shared.offerings()
            currentOffering = offerings.current
        } catch {
            // Non-fatal: paywall will show without offering if RC unreachable
        }
    }

    func purchase(package: Package) async throws {
        let result = try await Purchases.shared.purchase(package: package)
        isProUser = result.customerInfo.entitlements["pro"]?.isActive == true
    }

    func restorePurchases() async throws {
        let customerInfo = try await Purchases.shared.restorePurchases()
        isProUser = customerInfo.entitlements["pro"]?.isActive == true
    }

    func canStartCheckIn() -> Bool {
        isProUser || freeCheckInsUsed < freeLimit
    }

    func recordFreeCheckIn() {
        freeCheckInsUsed += 1
        UserDefaults.standard.set(freeCheckInsUsed, forKey: "freeCheckInsUsed")
    }
}
```

### 2.2 FoundationModelsService.swift

```swift
import FoundationModels
import Foundation

actor FoundationModelsService {
    private let session = LanguageModelSession()

    func analyze(
        energy: Int, sleep: Int, digestion: Int, emotion: Int, physical: Int
    ) async throws -> (ConstitutionType, [Recommendation]) {
        let prompt = buildPrompt(energy: energy, sleep: sleep, digestion: digestion, emotion: emotion, physical: physical)
        let response = try await session.respond(to: prompt)
        return try parseResponse(response.content)
    }

    private func buildPrompt(energy: Int, sleep: Int, digestion: Int, emotion: Int, physical: Int) -> String {
        """
        You are a Traditional Chinese Medicine wellness advisor. Based on today's wellness scores (1=lowest, 5=highest), determine the dominant TCM constitution and provide 3 personalized recommendations. Respond ONLY in valid JSON.

        Scores:
        - Energy level: \(energy)/5
        - Sleep quality: \(sleep)/5
        - Digestion comfort: \(digestion)/5
        - Emotional state: \(emotion)/5
        - Physical sensation: \(physical)/5

        JSON schema (respond exactly this structure, no markdown):
        {"constitution":"Wood|Fire|Earth|Metal|Water","food":"...","movement":"...","rest":"..."}

        TCM constitution guide:
        - Wood (木): Liver/Gallbladder. Signs: tension, frustration, tight muscles. Foods: sour, green leafy. Movement: stretching.
        - Fire (火): Heart/Small Intestine. Signs: anxiety, palpitations, joy. Foods: bitter, red. Movement: gentle cardio.
        - Earth (土): Spleen/Stomach. Signs: fatigue, worry, digestive issues. Foods: warm, sweet root veg. Movement: walking.
        - Metal (金): Lung/Large Intestine. Signs: grief, dryness, respiratory. Foods: white, pungent. Movement: breathing exercises.
        - Water (水): Kidney/Bladder. Signs: fear, cold, low energy. Foods: salty, dark. Movement: slow, restorative.
        """
    }

    private func parseResponse(_ text: String) throws -> (ConstitutionType, [Recommendation]) {
        let cleanText = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let data = cleanText.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: String],
              let constitutionStr = json["constitution"],
              let food = json["food"],
              let movement = json["movement"],
              let rest = json["rest"]
        else {
            throw FoundationModelsError.parseFailure
        }

        let constitution = ConstitutionType.from(string: constitutionStr)
        let recommendations: [Recommendation] = [
            Recommendation(category: .food, body: food),
            Recommendation(category: .movement, body: movement),
            Recommendation(category: .rest, body: rest)
        ]
        return (constitution, recommendations)
    }
}

enum FoundationModelsError: Error {
    case parseFailure
}
```

### 2.3 HealthKitService.swift

```swift
import HealthKit

actor HealthKitService {
    private let store = HKHealthStore()

    func requestAuthorization() async -> Bool {
        guard HKHealthStore.isHealthDataAvailable() else { return false }
        let typesToWrite: Set<HKSampleType> = [
            HKObjectType.categoryType(forIdentifier: .mindfulSession)!
        ]
        do {
            try await store.requestAuthorization(toShare: typesToWrite, read: [])
            return true
        } catch {
            return false
        }
    }

    func logCheckIn(date: Date) async {
        guard HKHealthStore.isHealthDataAvailable() else { return }
        let type = HKObjectType.categoryType(forIdentifier: .mindfulSession)!
        let sample = HKCategorySample(
            type: type,
            value: HKCategoryValue.notApplicable.rawValue,
            start: date,
            end: date.addingTimeInterval(120)  // 2-minute session
        )
        do {
            try await store.save(sample)
        } catch {
            // Silent fail — non-critical
        }
    }
}
```

---

## Phase 3: App Entry Point

### 3.1 ChiDailyApp.swift

```swift
import SwiftUI
import SwiftData
import RevenueCat

@main
struct ChiDailyApp: App {
    @State private var subscriptionService = SubscriptionService()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(subscriptionService)
                .modelContainer(for: CheckIn.self)
                .onAppear {
                    subscriptionService.configure()
                }
        }
    }
}
```

### 3.2 ContentView.swift

```swift
import SwiftUI

struct ContentView: View {
    @AppStorage("hasCompletedOnboarding") private var hasCompletedOnboarding = false
    @State private var showOnboarding = false

    var body: some View {
        if hasCompletedOnboarding {
            MainTabView()
        } else {
            OnboardingView(hasCompletedOnboarding: $hasCompletedOnboarding)
        }
    }
}

struct MainTabView: View {
    var body: some View {
        TabView {
            HomeView()
                .tabItem {
                    Label(NSLocalizedString("Today", comment: ""), systemImage: "sun.max")
                }
            HistoryView()
                .tabItem {
                    Label(NSLocalizedString("History", comment: ""), systemImage: "calendar")
                }
        }
        .tint(Color.chiAccent)
    }
}
```

---

## Phase 4: Onboarding

### 4.1 OnboardingView.swift

```swift
import SwiftUI

struct OnboardingView: View {
    @Binding var hasCompletedOnboarding: Bool
    @State private var currentPage = 0
    @Environment(SubscriptionService.self) private var subscriptionService

    var body: some View {
        TabView(selection: $currentPage) {
            OnboardingScreen1(onNext: { currentPage = 1 })
                .tag(0)
            OnboardingScreen2(onNext: { currentPage = 2 })
                .tag(1)
            OnboardingScreen3(
                onComplete: { hasCompletedOnboarding = true },
                onSkip: { hasCompletedOnboarding = true }
            )
            .tag(2)
        }
        .tabViewStyle(.page(indexDisplayMode: .always))
        .indexViewStyle(.page(backgroundDisplayMode: .always))
    }
}
```

### 4.2 OnboardingScreen3.swift (Soft Paywall)

```swift
import SwiftUI
import RevenueCat

struct OnboardingScreen3: View {
    let onComplete: () -> Void
    let onSkip: () -> Void

    @Environment(SubscriptionService.self) private var subscriptionService
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        VStack(spacing: Spacing.lg) {
            Spacer()

            Text(NSLocalizedString("Start Your Free Trial", comment: ""))
                .font(.largeTitle).bold()

            VStack(alignment: .leading, spacing: Spacing.sm) {
                FeatureRow(icon: "checkmark.circle.fill", text: NSLocalizedString("Unlimited daily check-ins", comment: ""))
                FeatureRow(icon: "checkmark.circle.fill", text: NSLocalizedString("On-device AI guidance", comment: ""))
                FeatureRow(icon: "checkmark.circle.fill", text: NSLocalizedString("HealthKit integration", comment: ""))
                FeatureRow(icon: "checkmark.circle.fill", text: NSLocalizedString("English + Japanese", comment: ""))
            }
            .padding(.horizontal, Spacing.lg)

            Spacer()

            VStack(spacing: Spacing.md) {
                if let offering = subscriptionService.currentOffering {
                    if let monthly = offering.monthly {
                        PrimaryButton(
                            title: String(format: NSLocalizedString("Start 7-Day Trial · %@/month", comment: ""), monthly.storeProduct.localizedPriceString)
                        ) {
                            Task { await purchaseMonthly(package: monthly) }
                        }
                    }
                    if let annual = offering.annual {
                        SecondaryOutlineButton(
                            title: String(format: NSLocalizedString("%@/year (save 42%%)", comment: ""), annual.storeProduct.localizedPriceString)
                        ) {
                            Task { await purchaseAnnual(package: annual) }
                        }
                    }
                }

                // CRITICAL: Maybe Later always visible
                Button(NSLocalizedString("Maybe Later", comment: "")) {
                    onSkip()
                }
                .font(.subheadline)
                .foregroundStyle(Color.secondary)

                Button(NSLocalizedString("Restore Purchases", comment: "")) {
                    Task { await restore() }
                }
                .font(.caption)
                .foregroundStyle(Color.secondary)
            }
            .padding(.horizontal, Spacing.lg)
            .padding(.bottom, Spacing.xl)
        }
        .task {
            await subscriptionService.fetchOfferings()
        }
    }

    private func purchaseMonthly(package: Package) async {
        isLoading = true
        do {
            try await subscriptionService.purchase(package: package)
            onComplete()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    private func purchaseAnnual(package: Package) async {
        isLoading = true
        do {
            try await subscriptionService.purchase(package: package)
            onComplete()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    private func restore() async {
        do {
            try await subscriptionService.restorePurchases()
            if subscriptionService.isProUser { onComplete() }
        } catch { }
    }
}
```

---

## Phase 5: Home + Check-in

### 5.1 HomeView.swift

```swift
import SwiftUI
import SwiftData

struct HomeView: View {
    @Query(sort: \CheckIn.date, order: .reverse) private var checkIns: [CheckIn]
    @Environment(SubscriptionService.self) private var subscriptionService
    @State private var showCheckIn = false
    @State private var showPaywall = false

    private var todayCheckIn: CheckIn? {
        checkIns.first { Calendar.current.isDateInToday($0.date) }
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: Spacing.lg) {
                    greetingSection
                    if let checkIn = todayCheckIn {
                        ResultSummaryCard(checkIn: checkIn)
                    } else {
                        startCheckInCard
                    }
                }
                .padding(Spacing.md)
            }
            .navigationTitle("Chi Daily")
            .navigationBarTitleDisplayMode(.inline)
        }
        .sheet(isPresented: $showCheckIn) {
            CheckInView()
        }
        .sheet(isPresented: $showPaywall) {
            PaywallView()
        }
    }

    private var greetingSection: some View {
        VStack(alignment: .leading) {
            Text(Date().formatted(.dateTime.weekday(.wide).month().day()))
                .font(.headline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var startCheckInCard: some View {
        VStack(spacing: Spacing.md) {
            Text(NSLocalizedString("How are you feeling today?", comment: ""))
                .font(.title2).bold()
            PrimaryButton(title: NSLocalizedString("Start Today's Check-in", comment: "")) {
                if subscriptionService.canStartCheckIn() {
                    showCheckIn = true
                } else {
                    showPaywall = true
                }
            }
        }
        .padding(Spacing.md)
        .background(Color.chiSurface)
        .cornerRadius(16)
    }
}
```

### 5.2 CheckInViewModel.swift

```swift
import SwiftUI
import SwiftData

@Observable
final class CheckInViewModel {
    var currentQuestion = 0
    var answers = [Int](repeating: 3, count: 5)  // Default to middle value
    var isAnalyzing = false
    var result: CheckIn?
    var error: String?

    private let foundationModels = FoundationModelsService()
    private let healthKit = HealthKitService()

    let questions: [CheckInQuestion] = [
        CheckInQuestion(key: "energy", title: NSLocalizedString("How is your energy today?", comment: "")),
        CheckInQuestion(key: "sleep", title: NSLocalizedString("How was your sleep last night?", comment: "")),
        CheckInQuestion(key: "digestion", title: NSLocalizedString("How is your digestion today?", comment: "")),
        CheckInQuestion(key: "emotions", title: NSLocalizedString("How are you feeling emotionally?", comment: "")),
        CheckInQuestion(key: "physical", title: NSLocalizedString("How does your body feel physically?", comment: ""))
    ]

    func selectAnswer(_ value: Int) {
        answers[currentQuestion] = value
    }

    func nextQuestion() {
        if currentQuestion < 4 {
            currentQuestion += 1
        }
    }

    func previousQuestion() {
        if currentQuestion > 0 {
            currentQuestion -= 1
        }
    }

    func submitCheckIn(modelContext: ModelContext) async {
        isAnalyzing = true
        defer { isAnalyzing = false }
        do {
            let (constitution, recommendations) = try await foundationModels.analyze(
                energy: answers[0], sleep: answers[1], digestion: answers[2],
                emotion: answers[3], physical: answers[4]
            )
            let checkIn = CheckIn(
                energyLevel: answers[0], sleepQuality: answers[1],
                digestionComfort: answers[2], emotionalState: answers[3],
                physicalSensation: answers[4],
                constitutionType: constitution.rawValue,
                foodRecommendation: recommendations.first(where: { $0.category == .food })?.body ?? "",
                movementRecommendation: recommendations.first(where: { $0.category == .movement })?.body ?? "",
                restRecommendation: recommendations.first(where: { $0.category == .rest })?.body ?? ""
            )
            modelContext.insert(checkIn)
            result = checkIn
            await healthKit.logCheckIn(date: checkIn.date)
        } catch {
            self.error = error.localizedDescription
        }
    }
}

struct CheckInQuestion {
    let key: String
    let title: String
}
```

### 5.3 CheckInView.swift

```swift
import SwiftUI
import SwiftData

struct CheckInView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext
    @State private var viewModel = CheckInViewModel()

    let options: [(emoji: String, label: String)] = [
        ("😴", NSLocalizedString("Very Low", comment: "")),
        ("😑", NSLocalizedString("Low", comment: "")),
        ("😊", NSLocalizedString("Moderate", comment: "")),
        ("😄", NSLocalizedString("Good", comment: "")),
        ("🌟", NSLocalizedString("Excellent", comment: ""))
    ]

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                progressBar
                if viewModel.isAnalyzing {
                    analyzingView
                } else if let result = viewModel.result {
                    ResultView(checkIn: result, onDone: { dismiss() })
                } else {
                    questionView
                }
            }
            .navigationTitle(NSLocalizedString("Today's Check-in", comment: ""))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(NSLocalizedString("Cancel", comment: "")) { dismiss() }
                }
            }
        }
    }

    private var progressBar: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Rectangle().fill(Color.secondary.opacity(0.2))
                Rectangle()
                    .fill(Color.chiAccent)
                    .frame(width: geo.size.width * CGFloat(viewModel.currentQuestion + 1) / 5)
                    .animation(.easeInOut, value: viewModel.currentQuestion)
            }
        }
        .frame(height: 4)
    }

    private var questionView: some View {
        VStack(spacing: Spacing.lg) {
            Text(viewModel.questions[viewModel.currentQuestion].title)
                .font(.headline)
                .multilineTextAlignment(.center)
                .padding(.horizontal, Spacing.lg)

            VStack(spacing: Spacing.sm) {
                ForEach(0..<5) { index in
                    let option = options[index]
                    QuestionRow(
                        option: index + 1,
                        label: option.label,
                        emoji: option.emoji,
                        isSelected: viewModel.answers[viewModel.currentQuestion] == index + 1,
                        onTap: { viewModel.selectAnswer(index + 1) }
                    )
                }
            }
            .padding(.horizontal, Spacing.md)

            Spacer()

            HStack(spacing: Spacing.md) {
                if viewModel.currentQuestion > 0 {
                    Button(NSLocalizedString("Back", comment: "")) {
                        viewModel.previousQuestion()
                    }
                    .buttonStyle(.bordered)
                }
                if viewModel.currentQuestion < 4 {
                    PrimaryButton(title: NSLocalizedString("Next →", comment: "")) {
                        viewModel.nextQuestion()
                    }
                } else {
                    PrimaryButton(title: NSLocalizedString("Get My Plan", comment: "")) {
                        Task { await viewModel.submitCheckIn(modelContext: modelContext) }
                    }
                }
            }
            .padding(.horizontal, Spacing.md)
            .padding(.bottom, Spacing.lg)
        }
    }

    private var analyzingView: some View {
        VStack(spacing: Spacing.lg) {
            Spacer()
            ProgressView()
                .scaleEffect(1.5)
            Text(NSLocalizedString("Analyzing your constitution...", comment: ""))
                .font(.headline)
                .foregroundStyle(.secondary)
            Spacer()
        }
    }
}
```

---

## Phase 6: Result + History

### 6.1 ResultView.swift

```swift
import SwiftUI

struct ResultView: View {
    let checkIn: CheckIn
    let onDone: (() -> Void)?
    private let constitution: ConstitutionType

    init(checkIn: CheckIn, onDone: (() -> Void)? = nil) {
        self.checkIn = checkIn
        self.onDone = onDone
        self.constitution = ConstitutionType.from(string: checkIn.constitutionType)
    }

    var body: some View {
        ScrollView {
            VStack(spacing: Spacing.xl) {
                ConstitutionBadge(type: constitution)
                    .padding(.top, Spacing.xl)

                Divider()

                VStack(spacing: Spacing.md) {
                    RecommendationCard(
                        category: .food,
                        title: NSLocalizedString("Food", comment: ""),
                        body: checkIn.foodRecommendation
                    )
                    RecommendationCard(
                        category: .movement,
                        title: NSLocalizedString("Movement", comment: ""),
                        body: checkIn.movementRecommendation
                    )
                    RecommendationCard(
                        category: .rest,
                        title: NSLocalizedString("Rest", comment: ""),
                        body: checkIn.restRecommendation
                    )
                }
                .padding(.horizontal, Spacing.md)

                if let onDone = onDone {
                    PrimaryButton(title: NSLocalizedString("Done ✓", comment: "")) { onDone() }
                        .padding(.horizontal, Spacing.md)
                        .padding(.bottom, Spacing.xl)
                }
            }
        }
    }
}
```

### 6.2 HistoryView.swift

```swift
import SwiftUI
import SwiftData

struct HistoryView: View {
    @Query(sort: \CheckIn.date, order: .reverse) private var checkIns: [CheckIn]

    var body: some View {
        NavigationStack {
            Group {
                if checkIns.isEmpty {
                    emptyState
                } else {
                    List(checkIns) { checkIn in
                        NavigationLink {
                            ResultView(checkIn: checkIn)
                                .navigationTitle(checkIn.date.formatted(.dateTime.month().day()))
                        } label: {
                            HistoryRow(checkIn: checkIn)
                        }
                    }
                }
            }
            .navigationTitle(NSLocalizedString("History", comment: ""))
        }
    }

    private var emptyState: some View {
        VStack(spacing: Spacing.md) {
            Image(systemName: "calendar.badge.plus")
                .font(.system(size: 48))
                .foregroundStyle(Color.secondary)
            Text(NSLocalizedString("Complete your first check-in to see history", comment: ""))
                .font(.headline)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
        }
        .padding(Spacing.xl)
    }
}

struct HistoryRow: View {
    let checkIn: CheckIn
    private var constitution: ConstitutionType { ConstitutionType.from(string: checkIn.constitutionType) }

    var body: some View {
        HStack {
            Image(systemName: constitution.icon)
                .foregroundStyle(constitution.color)
            VStack(alignment: .leading) {
                Text(checkIn.date.formatted(.dateTime.weekday(.wide).month().day()))
                    .font(.headline)
                Text(constitution.rawValue)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, Spacing.xs)
    }
}
```

---

## Phase 7: Localization

### en.lproj/Localizable.strings

```
"Today" = "Today";
"History" = "History";
"Start Today's Check-in" = "Start Today's Check-in";
"How are you feeling today?" = "How are you feeling today?";
"Today's Check-in" = "Today's Check-in";
"Start 7-Day Trial · %@/month" = "Start 7-Day Trial · %@/month";
"%@/year (save 42%%)" = "%@/year (save 42%%)";
"Maybe Later" = "Maybe Later";
"Restore Purchases" = "Restore Purchases";
"Food" = "Food";
"Movement" = "Movement";
"Rest" = "Rest";
"Done ✓" = "Done ✓";
"Analyzing your constitution..." = "Analyzing your constitution...";
"Complete your first check-in to see history" = "Complete your first check-in to see history";
"Get My Plan" = "Get My Plan";
"Next →" = "Next →";
"Back" = "Back";
"Cancel" = "Cancel";
"How is your energy today?" = "How is your energy today?";
"How was your sleep last night?" = "How was your sleep last night?";
"How is your digestion today?" = "How is your digestion today?";
"How are you feeling emotionally?" = "How are you feeling emotionally?";
"How does your body feel physically?" = "How does your body feel physically?";
"Very Low" = "Very Low";
"Low" = "Low";
"Moderate" = "Moderate";
"Good" = "Good";
"Excellent" = "Excellent";
```

### ja.lproj/Localizable.strings

```
"Today" = "今日";
"History" = "履歴";
"Start Today's Check-in" = "今日のチェックインを始める";
"How are you feeling today?" = "今日の体調はいかがですか？";
"Today's Check-in" = "今日のチェックイン";
"Start 7-Day Trial · %@/month" = "7日間無料体験を始める · %@/月";
"%@/year (save 42%%)" = "%@/年（42%%お得）";
"Maybe Later" = "後で";
"Restore Purchases" = "購入を復元";
"Food" = "食事";
"Movement" = "運動";
"Rest" = "休息";
"Done ✓" = "完了 ✓";
"Analyzing your constitution..." = "体質を分析中...";
"Complete your first check-in to see history" = "最初のチェックインを完了して履歴を表示";
"Get My Plan" = "プランを取得";
"Next →" = "次へ →";
"Back" = "戻る";
"Cancel" = "キャンセル";
"How is your energy today?" = "今日のエネルギーレベルは？";
"How was your sleep last night?" = "昨夜の睡眠はどうでしたか？";
"How is your digestion today?" = "今日の消化の状態は？";
"How are you feeling emotionally?" = "感情的な状態はいかがですか？";
"How does your body feel physically?" = "体の感覚はどうですか？";
"Very Low" = "とても低い";
"Low" = "低い";
"Moderate" = "普通";
"Good" = "良い";
"Excellent" = "とても良い";
```

---

## Phase 8: Build Verification

```bash
# After implementation, verify:
cd ChiDailyios

# 1. No Mock implementations
grep -r 'Mock' --include='*.swift' . | grep -v 'Tests/' | grep -v '.build/' | wc -l
# Expected: 0

# 2. RevenueCat imported
grep -r 'import RevenueCat' --include='*.swift' . | wc -l
# Expected: > 0

# 3. RevenueCatUI NOT imported (CRITICAL Rule #20)
grep -r 'import RevenueCatUI' --include='*.swift' . | wc -l
# Expected: 0

# 4. Build succeeds
xcodebuild -scheme ChiDailyios -destination 'platform=iOS Simulator,name=iPhone 16' build
# Expected: BUILD SUCCEEDED
```
