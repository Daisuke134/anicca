import SwiftUI
import UIKit

enum InitialExperienceStyle {
    static var accent: Color { AppTheme.Colors.accent }
    static var background: some View { AppBackground() }
}

/// Scroll long copy while keeping the next action reachable above the safe area.
struct OnboardingPage<Content: View, Footer: View>: View {
    private let alignment: HorizontalAlignment
    private let content: Content
    private let footer: Footer

    init(
        alignment: HorizontalAlignment = .center,
        @ViewBuilder content: () -> Content,
        @ViewBuilder footer: () -> Footer
    ) {
        self.alignment = alignment
        self.content = content()
        self.footer = footer()
    }

    var body: some View {
        GeometryReader { geometry in
            ScrollView {
                VStack(alignment: alignment, spacing: 20) {
                    content
                }
                .padding(.horizontal, 24)
                .padding(.vertical, 20)
                .frame(maxWidth: .infinity, minHeight: geometry.size.height)
            }
            .scrollDismissesKeyboard(.interactively)
        }
        .safeAreaInset(edge: .bottom, spacing: 0) {
            footer
                .padding(.horizontal, 24)
                .padding(.top, 12)
                .padding(.bottom, 16)
        }
        .foregroundStyle(AppTheme.Colors.label)
        .background(InitialExperienceStyle.background)
    }
}

struct AffirmationGoalStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState
    @State private var selection = "self_love"

    private let options = [
        ("self_love", "growth_goal_self_love", "heart"),
        ("calm", "growth_goal_calm", "leaf"),
        ("confidence", "growth_goal_confidence", "sun.max"),
        ("focus", "growth_goal_focus", "scope"),
        ("letting_go", "growth_goal_letting_go", "wind")
    ]

    var body: some View {
        OnboardingPage(alignment: .leading) {
            Text("Anicca").font(.system(.title, design: .serif))
            Spacer(minLength: 12)
            Text(String(localized: "growth_goal_title"))
                .font(AppTheme.Typography.onboardingTitle)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)
            Text(String(localized: "growth_goal_subtitle"))
                .font(.subheadline)
                .foregroundStyle(AppTheme.Colors.secondaryLabel)
                .fixedSize(horizontal: false, vertical: true)
            ForEach(options, id: \.0) { option in
                Button {
                    // Selection feedback while a value changes (Apple HIG, Playing haptics).
                    UISelectionFeedbackGenerator().selectionChanged()
                    selection = option.0
                } label: {
                    HStack(spacing: 14) {
                        Image(systemName: option.2).frame(width: 24)
                        Text(String(localized: String.LocalizationValue(option.1)))
                            .fixedSize(horizontal: false, vertical: true)
                        Spacer(minLength: 8)
                        Image(systemName: selection == option.0 ? "checkmark.circle.fill" : "circle")
                            .foregroundStyle(selection == option.0 ? AppTheme.Colors.accent : AppTheme.Colors.secondaryLabel)
                    }
                    .padding(18)
                    .selectionCard(isSelected: selection == option.0)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("onboarding-goal-\(option.0)")
                .accessibilityAddTraits(selection == option.0 ? .isSelected : [])
            }
            Spacer(minLength: 12)
        } footer: {
            PrimaryButton(title: String(localized: "common_continue"), action: saveAndContinue)
                .accessibilityIdentifier("onboarding-goal-continue")
        }
        .onAppear {
            selection = appState.personalizationProfile.desiredState.flatMap { value in options.contains(where: { $0.0 == value }) ? value : nil }
                ?? appState.userProfile.goals.first.flatMap { value in options.contains(where: { $0.0 == value }) ? value : nil } ?? "self_love"
        }
    }

    private func saveAndContinue() {
        var profile = appState.userProfile
        profile.goals = [selection]
        appState.updateUserProfile(profile, sync: true)
        var personalization = appState.personalizationProfile
        personalization.desiredState = selection
        appState.updatePersonalizationProfile(personalization)
        next()
    }
}

struct PreferredNameStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState
    @State private var name = ""

    var body: some View {
        OnboardingPage(alignment: .leading) {
            Text("Anicca").font(.system(.title, design: .serif))
            Spacer(minLength: 24)
            Text(String(localized: "growth_name_title"))
                .font(AppTheme.Typography.onboardingTitle)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)
            Text(String(localized: "growth_name_optional_hint"))
                .font(.subheadline)
                .foregroundStyle(AppTheme.Colors.secondaryLabel)
                .fixedSize(horizontal: false, vertical: true)
            TextField(String(localized: "growth_name_placeholder"), text: $name)
                .textInputAutocapitalization(.words)
                .textContentType(.givenName)
                .autocorrectionDisabled()
                .submitLabel(.continue)
                .padding(18)
                .selectionCard(isSelected: false)
                .accessibilityIdentifier("onboarding-name-field")
                .onSubmit(saveAndContinue)
            Spacer(minLength: 24)
        } footer: {
            PrimaryButton(title: String(localized: "common_continue"), action: saveAndContinue)
                .accessibilityIdentifier("onboarding-name-continue")
        }
        .onAppear { name = appState.personalizationProfile.preferredName ?? "" }
    }

    private func saveAndContinue() {
        var personalization = appState.personalizationProfile
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        personalization.preferredName = trimmed.isEmpty ? nil : trimmed
        appState.updatePersonalizationProfile(personalization)
        next()
    }
}

struct FirstAffirmationStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState
    @StateObject private var likedStore = LikedQuotesStore()
    @State private var selection: PersonalizedNudgeSelector.Selection?
    @State private var deliveryId: String?
    @State private var revealComplete = false

    var body: some View {
        OnboardingPage {
            Text("Anicca").font(.system(.title, design: .serif))
            Spacer(minLength: 16)
            if let quote = selection?.quote {
                AffirmationRevealCard(
                    quote: quote,
                    answerSnapshot: appState.syntheticUser.answerSnapshot,
                    preferredName: appState.personalizationProfile.preferredName,
                    identifier: "onboarding-first-affirmation",
                    isRevealed: $revealComplete
                )
            }
            Text(String(localized: "growth_first_subtitle"))
                .font(.subheadline).foregroundStyle(AppTheme.Colors.secondaryLabel)
                .multilineTextAlignment(.center).fixedSize(horizontal: false, vertical: true)
            Button {
                guard let quote = selection?.quote else { return }
                let liked = likedStore.toggle(quote, themeID: ThemeStore().selected.rawValue)
                // Same impact feedback as the home card's like action
                // (QuoteCardView), so the save moment feels identical.
                UIImpactFeedbackGenerator(style: .soft).impactOccurred()
                if liked, let deliveryId {
                    DecisionPointRecorder.shared.recordResponse(deliveryId: deliveryId, event: .saved)
                }
                AnalyticsManager.shared.track(liked ? .affirmationLiked : .affirmationUnliked, properties: ["quote_id": quote.id, "category": quote.categoryID, "source": "onboarding"])
            } label: {
                Label(String(localized: likedStore.isLiked(selection?.quote.id ?? "") ? "growth_saved" : "growth_keep_close"),
                      systemImage: likedStore.isLiked(selection?.quote.id ?? "") ? "heart.fill" : "heart")
                    .font(.subheadline).padding(14)
                    .background(AppTheme.Colors.cardBackground.opacity(0.8))
                    .clipShape(RoundedRectangle(cornerRadius: 18))
                    .contentShape(Rectangle())
            }
            .buttonStyle(PressScaleButtonStyle())
            .disabled(!revealComplete)
            .accessibilityIdentifier("onboarding-first-save")
            Spacer(minLength: 16)
        } footer: {
            PrimaryButton(title: String(localized: "growth_set_reminders"), isEnabled: revealComplete) {
                if let quote = selection?.quote {
                    DailyAffirmationStore.shared.seed(quote, language: appState.effectiveLanguage.rawValue, deliveryId: deliveryId)
                }
                if let deliveryId { DecisionPointRecorder.shared.recordResponse(deliveryId: deliveryId, event: .responded) }
                next()
            }
                .accessibilityIdentifier("onboarding-first-continue")
        }
        .onAppear {
            computeSelectionIfNeeded()
        }
        .onChange(of: revealComplete) { revealed in
            if revealed, let quote = selection?.quote {
                if let deliveryId {
                    DecisionPointRecorder.shared.recordDelivery(deliveryId: deliveryId, messageId: quote.id, source: "onboarding")
                }
                AnalyticsManager.shared.track(.firstAffirmationViewed, properties: ["quote_id": quote.id, "category": quote.categoryID])
            }
        }
    }

    private func computeSelectionIfNeeded() {
        guard selection == nil else { return }
        let user = appState.syntheticUser
        if let carryover = PersonalizedNudgeSelector.previewCarryoverSelection(
            cases: DecisionPointStore.shared.allCases(), personId: user.personId,
            preferredLanguage: appState.effectiveLanguage) {
            selection = carryover.selection
            deliveryId = carryover.deliveryId
            return
        }
        let band = PersonalizedNudgeSelector.TimeBand.band(forHour: Calendar.current.component(.hour, from: Date()))
        selection = OnboardingManagerPrior.select(
            user: user,
            pool: QuoteProvider.shared.all(preferredLanguage: appState.effectiveLanguage),
            band: band
        )
        if let selection, deliveryId == nil {
            deliveryId = DecisionPointRecorder.shared.recordDecision(selection: selection, syntheticUser: user, source: "onboarding_first_intervention")
        }
    }
}

/// The answer dissolves into the selected words on the same theme card.
private struct AffirmationRevealCard: View {
    let quote: Quote
    let answerSnapshot: OnboardingAnswerSnapshot
    let preferredName: String?
    let identifier: String
    @Binding var isRevealed: Bool
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @StateObject private var themeStore = ThemeStore()
    @State private var phase: Phase = .answer

    private enum Phase { case answer, transforming, result }

    private var answerLabel: String {
        let goal = answerSnapshot.values["desired_state"]?.first ?? "unknown"
        guard ["calm", "confidence", "focus", "self_love", "letting_go"].contains(goal) else {
            return String(localized: "growth_first_affirmation")
        }
        return NSLocalizedString("growth_goal_\(goal)", comment: "")
    }

    var body: some View {
        VStack(spacing: 20) {
            Text(String(localized: "growth_first_affirmation"))
                .font(.caption).tracking(2)
            if let preferredName {
                Text(String(format: NSLocalizedString("growth_first_for_name", comment: ""), preferredName))
                    .font(.subheadline)
            }
            ZStack {
                Text(answerLabel)
                    .font(AppTheme.Typography.onboardingTitle)
                    .opacity(phase == .answer ? 1 : 0)
                    .accessibilityHidden(phase != .answer)
                Text(quote.text)
                    .font(AppTheme.Typography.onboardingTitle)
                    .opacity(phase == .result ? 1 : 0)
                    .accessibilityHidden(phase != .result)
                    .accessibilityIdentifier(identifier)
            }
            .frame(minHeight: 180)
        }
        .multilineTextAlignment(.center)
        .fixedSize(horizontal: false, vertical: true)
        .frame(maxWidth: .infinity)
        .padding(24)
        .foregroundStyle(themeStore.selected.foregroundColor)
        .background {
            GeometryReader { geometry in
                themeStore.image.resizable().scaledToFill()
                    .frame(width: geometry.size.width, height: geometry.size.height)
                    .clipped()
                    .opacity(phase == .answer ? 0.35 : 1)
            }
            .accessibilityHidden(true)
        }
        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.cardLarge))
        .task(id: quote.id) { await reveal() }
        .onChange(of: reduceMotion) { reduced in
            if reduced { phase = .result; isRevealed = true }
        }
    }

    @MainActor
    private func reveal() async {
        if reduceMotion { phase = .result; isRevealed = true; return }
        phase = .answer
        isRevealed = false
        do {
            try await Task.sleep(nanoseconds: 180_000_000)
            guard !reduceMotion else { return }
            withAnimation(.easeInOut(duration: 0.22)) { phase = .transforming }
            try await Task.sleep(nanoseconds: 220_000_000)
            guard !reduceMotion else { return }
            withAnimation(.easeOut(duration: 0.24)) { phase = .result }
            isRevealed = true
        } catch {
            // Leaving this screen cancels its task; no delayed state reaches the next screen.
        }
    }
}

struct ReminderScheduleStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState
    @State private var selectedSlots: Set<NudgeSlot> = []
    @State private var frequency = 1
    @State private var didInitialize = false

    private var sortedSlots: [NudgeSlot] { selectedSlots.sorted() }

    var body: some View {
        OnboardingPage(alignment: .leading) {
            Text("Anicca").font(.system(.title, design: .serif))
            Text(String(localized: "growth_reminder_title"))
                .font(AppTheme.Typography.onboardingTitle)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)
            // Founder rule (2026-11-22): notification timing is the model's
            // decision, never a question to the user. This step used to ask
            // "When should we reach you?" and "How many moments a day?" —
            // that ask itself is the design error. The step now only says
            // that Anicca chooses the moment. The schedule saved on continue
            // is the rules proposal from initializeIfNeeded (not a user
            // choice), so local delivery keeps working while the server
            // decision engine takes over timing.
            Text(String(localized: "growth_reminder_model_timing"))
                .font(.subheadline).foregroundStyle(AppTheme.Colors.secondaryLabel)
                .fixedSize(horizontal: false, vertical: true)
        } footer: {
            PrimaryButton(title: String(localized: "common_continue"), isEnabled: true) {
                save()
                next()
            }
            .accessibilityIdentifier("onboarding-reminder-continue")
        }
        .onAppear { initializeIfNeeded() }
    }

    private func initializeIfNeeded() {
        guard !didInitialize else { return }
        didInitialize = true
        let profile = appState.syntheticUser.conditioningProfile
        frequency = profile.nudgeSlots.isEmpty
            ? PersonalizationRules.proposedFrequency(struggleFrequency: profile.struggleFrequency) : profile.dailyFrequency
        let proposed = PersonalizationRules.initialSlots(user: appState.syntheticUser, frequency: frequency)
        selectedSlots = Set(proposed.filter { !PersonalizationRules.isQuiet($0, quietHours: profile.answers.ids(for: .quietHours)) })
        if profile.nudgeSlots.isEmpty { frequency = max(1, min(frequency, selectedSlots.count)) }
    }

    private func save() {
        var profile = appState.personalizationProfile
        profile.nudgeSlots = sortedSlots
        profile.dailyFrequency = frequency
        appState.updatePersonalizationProfile(profile)
    }
}

struct FirstInterventionStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState
    @State private var selection: PersonalizedNudgeSelector.Selection?
    @State private var deliveryId: String?
    @State private var revealComplete = false

    private var nextSlotLabel: String? {
        PersonalizationRules.effectiveSlots(user: appState.syntheticUser).first?.label
    }

    var body: some View {
        OnboardingPage {
            Text("Anicca").font(.system(.title, design: .serif))
            Spacer(minLength: 16)
            if let quote = selection?.quote {
                AffirmationRevealCard(
                    quote: quote,
                    answerSnapshot: appState.syntheticUser.answerSnapshot,
                    preferredName: appState.personalizationProfile.preferredName,
                    identifier: "onboarding-first-intervention",
                    isRevealed: $revealComplete
                )
            }
            if let nextSlotLabel {
                Text(String(format: NSLocalizedString("growth_first_next_time", comment: ""), nextSlotLabel))
                    .font(.subheadline).foregroundStyle(AppTheme.Colors.secondaryLabel)
                    .multilineTextAlignment(.center).fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 16)
        } footer: {
            PrimaryButton(title: String(localized: "growth_open_today"), isEnabled: revealComplete) {
                if let quote = selection?.quote {
                    DailyAffirmationStore.shared.seed(quote, language: appState.effectiveLanguage.rawValue, deliveryId: deliveryId)
                }
                if let deliveryId {
                    DecisionPointRecorder.shared.recordResponse(deliveryId: deliveryId, event: .responded)
                }
                next()
            }
            .accessibilityIdentifier("onboarding-intervention-continue")
        }
        .onAppear { computeSelectionIfNeeded() }
        .onChange(of: revealComplete) { revealed in
            if revealed, let quote = selection?.quote {
                if let deliveryId {
                    DecisionPointRecorder.shared.recordDelivery(deliveryId: deliveryId, messageId: quote.id, source: "onboarding")
                }
                AnalyticsManager.shared.track(.firstAffirmationViewed, properties: [
                    "quote_id": quote.id, "category": quote.categoryID, "source": "first_intervention"
                ])
            }
        }
    }

    private func computeSelectionIfNeeded() {
        guard selection == nil else { return }
        let user = appState.syntheticUser
        // The words revealed in the preview step are this person's first
        // affirmation. Carry that exact quote into the first intervention —
        // and from there into the home card — instead of selecting a second,
        // different quote here. Falls back to a fresh selection when no
        // preview decision exists for this person.
        if let carryover = PersonalizedNudgeSelector.previewCarryoverSelection(
            cases: DecisionPointStore.shared.allCases(),
            personId: DecisionPointRecorder.shared.personId,
            preferredLanguage: appState.effectiveLanguage
        ) {
            selection = carryover.selection
            deliveryId = carryover.deliveryId
            return
        }
        let band = PersonalizedNudgeSelector.TimeBand.band(forHour: Calendar.current.component(.hour, from: Date()))
        selection = OnboardingManagerPrior.select(
            user: user,
            pool: QuoteProvider.shared.all(preferredLanguage: appState.effectiveLanguage),
            band: band
        )
        if let selection, deliveryId == nil {
            deliveryId = DecisionPointRecorder.shared.recordDecision(selection: selection, syntheticUser: user, source: "onboarding_first_intervention")
        }
    }
}
