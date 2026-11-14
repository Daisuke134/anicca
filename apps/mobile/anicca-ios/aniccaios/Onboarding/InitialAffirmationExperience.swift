import SwiftUI

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
        ("focus", "growth_goal_focus", "scope")
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
    @State private var didRecordDecision = false

    private var legacyQuote: Quote {
        let quoteIDs = ["self_love": "q013", "calm": "q021", "confidence": "q041", "letting_go": "q071"]
        let id = quoteIDs[appState.userProfile.goals.first ?? "self_love"] ?? "q013"
        return QuoteProvider.shared.byId(id, preferredLanguage: appState.effectiveLanguage)
            ?? QuoteProvider.shared.all(preferredLanguage: appState.effectiveLanguage)[0]
    }

    private var quote: Quote { selection?.quote ?? legacyQuote }

    var body: some View {
        OnboardingPage {
            Text("Anicca").font(.system(.title, design: .serif))
            Spacer(minLength: 16)
            affirmationIcon
            Text(String(localized: "growth_first_affirmation"))
                .font(.caption).tracking(2)
                .foregroundStyle(AppTheme.Colors.secondaryLabel)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
            if let name = appState.personalizationProfile.preferredName {
                Text(String(format: NSLocalizedString("growth_first_for_name", comment: ""), name))
                    .font(.subheadline).foregroundStyle(AppTheme.Colors.secondaryLabel)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Text(quote.text)
                .font(AppTheme.Typography.onboardingTitle)
                .multilineTextAlignment(.center).fixedSize(horizontal: false, vertical: true)
                .accessibilityIdentifier("onboarding-first-affirmation")
            Text(String(localized: "growth_first_subtitle"))
                .font(.subheadline).foregroundStyle(AppTheme.Colors.secondaryLabel)
                .multilineTextAlignment(.center).fixedSize(horizontal: false, vertical: true)
            Button {
                let liked = likedStore.toggle(quote)
                AnalyticsManager.shared.track(liked ? .affirmationLiked : .affirmationUnliked, properties: ["quote_id": quote.id, "category": quote.categoryID, "source": "onboarding"])
            } label: {
                Label(String(localized: likedStore.isLiked(quote.id) ? "growth_saved" : "growth_keep_close"),
                      systemImage: likedStore.isLiked(quote.id) ? "heart.fill" : "heart")
                    .font(.subheadline).padding(14)
                    .background(AppTheme.Colors.cardBackground.opacity(0.8))
                    .clipShape(RoundedRectangle(cornerRadius: 18))
            }
            .buttonStyle(.plain)
            .accessibilityIdentifier("onboarding-first-save")
            Spacer(minLength: 16)
        } footer: {
            PrimaryButton(title: String(localized: "growth_set_reminders"), action: next)
                .accessibilityIdentifier("onboarding-first-continue")
        }
        .onAppear {
            computeSelectionIfNeeded()
            AnalyticsManager.shared.track(.firstAffirmationViewed, properties: ["quote_id": quote.id, "category": quote.categoryID])
        }
    }

    private func computeSelectionIfNeeded() {
        guard selection == nil else { return }
        let profile = appState.personalizationProfile
        guard profile.hasAnswers else { return }
        let band = PersonalizedNudgeSelector.TimeBand.band(forHour: Calendar.current.component(.hour, from: Date()))
        selection = PersonalizedNudgeSelector.select(
            profile: profile,
            pool: QuoteProvider.shared.all(preferredLanguage: appState.effectiveLanguage),
            shownAt: DecisionPointStore.shared.shownTimestamps(),
            band: band
        )
        if let selection, !didRecordDecision {
            didRecordDecision = true
            DecisionPointRecorder.shared.recordDecision(selection: selection, profile: profile, source: "onboarding_preview")
        }
    }
}

private var affirmationIcon: some View {
    Image(systemName: "sun.max")
        .font(.system(size: 46, weight: .ultraLight))
        .foregroundStyle(InitialExperienceStyle.accent)
        .padding(24)
        .background(Circle().fill(AppTheme.Colors.habitAccent.opacity(0.2)))
        .accessibilityHidden(true)
}

struct ReminderScheduleStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState
    @State private var selectedSlots: Set<NudgeSlot> = []
    @State private var frequency = 1
    @State private var didInitialize = false

    private var sortedSlots: [NudgeSlot] { selectedSlots.sorted() }
    private var isValid: Bool {
        PersonalizationRules.isValidSchedule(slots: sortedSlots, frequency: frequency)
    }

    var body: some View {
        OnboardingPage(alignment: .leading) {
            Text("Anicca").font(.system(.title, design: .serif))
            Text(String(localized: "growth_reminder_title"))
                .font(AppTheme.Typography.onboardingTitle)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)
            Text(String(localized: "growth_reminder_explanation"))
                .font(.subheadline).foregroundStyle(AppTheme.Colors.secondaryLabel)
                .fixedSize(horizontal: false, vertical: true)
            VStack(alignment: .leading, spacing: 10) {
                Text(String(localized: "growth_slots_title"))
                    .font(.headline).fixedSize(horizontal: false, vertical: true)
                ForEach(PersonalizationRules.presetSlots, id: \.self) { slot in
                    Button {
                        toggle(slot)
                    } label: {
                        HStack(spacing: 14) {
                            Text(slot.label)
                            Spacer()
                            Image(systemName: selectedSlots.contains(slot) ? "checkmark.circle.fill" : "circle")
                                .foregroundStyle(selectedSlots.contains(slot) ? AppTheme.Colors.accent : AppTheme.Colors.secondaryLabel)
                        }
                        .padding(14)
                        .selectionCard(isSelected: selectedSlots.contains(slot))
                    }
                    .buttonStyle(.plain)
                    .accessibilityIdentifier("onboarding-slot-\(slot.hour)")
                    .accessibilityAddTraits(selectedSlots.contains(slot) ? .isSelected : [])
                }
            }
            VStack(alignment: .leading, spacing: 10) {
                Text(String(localized: "growth_frequency_title"))
                    .font(.headline).fixedSize(horizontal: false, vertical: true)
                HStack(spacing: 10) {
                    ForEach(1...PersonalizationRules.freeFrequencyCap, id: \.self) { count in
                        Button { frequency = count } label: {
                            HStack(spacing: 8) {
                                Text("\(count)").font(.headline)
                                Image(systemName: frequency == count ? "checkmark.circle.fill" : "circle")
                                    .foregroundStyle(frequency == count ? AppTheme.Colors.accent : AppTheme.Colors.secondaryLabel)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(14)
                            .selectionCard(isSelected: frequency == count)
                        }
                        .buttonStyle(.plain)
                        .accessibilityIdentifier("onboarding-frequency-\(count)")
                        .accessibilityAddTraits(frequency == count ? .isSelected : [])
                    }
                }
                if frequency > selectedSlots.count {
                    Text(String(localized: "growth_slots_need_more"))
                        .font(.caption).foregroundStyle(AppTheme.Colors.secondaryLabel)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        } footer: {
            PrimaryButton(title: String(localized: "common_continue"), isEnabled: isValid) {
                save()
                next()
            }
            .accessibilityIdentifier("onboarding-reminder-continue")
        }
        .onAppear { initializeIfNeeded() }
    }

    private func toggle(_ slot: NudgeSlot) {
        if selectedSlots.contains(slot) {
            selectedSlots.remove(slot)
        } else if selectedSlots.count < PersonalizationRules.freeFrequencyCap {
            selectedSlots.insert(slot)
        }
    }

    private func initializeIfNeeded() {
        guard !didInitialize else { return }
        didInitialize = true
        let profile = appState.personalizationProfile
        if !profile.nudgeSlots.isEmpty {
            selectedSlots = Set(profile.nudgeSlots)
            frequency = profile.dailyFrequency
        } else {
            frequency = PersonalizationRules.proposedFrequency(struggleFrequency: profile.struggleFrequency)
            selectedSlots = Set(PersonalizationRules.proposedSlots(painPointIds: profile.painPointIds, frequency: frequency))
        }
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
    @State private var didRecordDecision = false

    private var nextSlotLabel: String? {
        appState.personalizationProfile.nudgeSlots.sorted().first?.label
    }

    var body: some View {
        OnboardingPage {
            Text("Anicca").font(.system(.title, design: .serif))
            Spacer(minLength: 16)
            affirmationIcon
            Text(String(localized: "growth_first_affirmation"))
                .font(.caption).tracking(2).foregroundStyle(AppTheme.Colors.secondaryLabel)
                .multilineTextAlignment(.center).fixedSize(horizontal: false, vertical: true)
            if let name = appState.personalizationProfile.preferredName {
                Text(String(format: NSLocalizedString("growth_first_for_name", comment: ""), name))
                    .font(.subheadline).foregroundStyle(AppTheme.Colors.secondaryLabel)
                    .multilineTextAlignment(.center).fixedSize(horizontal: false, vertical: true)
            }
            if let quote = selection?.quote {
                Text(quote.text)
                    .font(AppTheme.Typography.onboardingTitle)
                    .multilineTextAlignment(.center).fixedSize(horizontal: false, vertical: true)
                    .accessibilityIdentifier("onboarding-first-intervention")
            }
            if let nextSlotLabel {
                Text(String(format: NSLocalizedString("growth_first_next_time", comment: ""), nextSlotLabel))
                    .font(.subheadline).foregroundStyle(AppTheme.Colors.secondaryLabel)
                    .multilineTextAlignment(.center).fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 16)
        } footer: {
            PrimaryButton(title: String(localized: "growth_open_today")) {
                if let quote = selection?.quote {
                    DailyAffirmationStore.shared.seed(quote, language: appState.effectiveLanguage.rawValue)
                }
                next()
            }
            .accessibilityIdentifier("onboarding-intervention-continue")
        }
        .onAppear { computeSelectionIfNeeded() }
    }

    private func computeSelectionIfNeeded() {
        guard selection == nil else { return }
        let profile = appState.personalizationProfile
        let band = PersonalizedNudgeSelector.TimeBand.band(forHour: Calendar.current.component(.hour, from: Date()))
        selection = PersonalizedNudgeSelector.select(
            profile: profile,
            pool: QuoteProvider.shared.all(preferredLanguage: appState.effectiveLanguage),
            shownAt: DecisionPointStore.shared.shownTimestamps(),
            band: band
        )
        if let selection, !didRecordDecision {
            didRecordDecision = true
            DecisionPointRecorder.shared.recordDecision(selection: selection, profile: profile, source: "onboarding_first_intervention")
            AnalyticsManager.shared.track(.firstAffirmationViewed, properties: [
                "quote_id": selection.quote.id,
                "category": selection.quote.categoryID,
                "source": "first_intervention"
            ])
        }
    }
}
