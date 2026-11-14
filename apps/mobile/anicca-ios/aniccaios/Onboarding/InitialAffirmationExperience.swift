import SwiftUI

enum InitialExperienceStyle {
    static let accent = Color(red: 0.19, green: 0.36, blue: 0.27)

    static var background: some View {
        LinearGradient(
            colors: [AppTheme.Colors.background, Color(light: Color(hex: "#e4ecdc"), dark: Color(hex: "#26392d"))],
            startPoint: .topTrailing, endPoint: .bottomLeading
        ).ignoresSafeArea()
    }
}

struct AffirmationGoalStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState
    @State private var selection: String = "self_love"
    @State private var name: String = ""

    /// Phase 1 desired-state answer set from the answer→change mapping:
    /// calm / confidence / focus / self_love. (The previous "letting_go"
    /// option is not part of the mapping; stored legacy values fall back to
    /// the default below and stay usable by the feed's legacy goal map.)
    private let options = [
        ("self_love", "growth_goal_self_love", "heart"),
        ("calm", "growth_goal_calm", "leaf"),
        ("confidence", "growth_goal_confidence", "sun.max"),
        ("focus", "growth_goal_focus", "scope")
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("Anicca").font(.system(size: 28, design: .serif)).padding(.top, 20)
            Spacer(minLength: 12)
            Text(String(localized: "growth_goal_title"))
                .font(.system(.largeTitle, design: .serif)).fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)
            Text(String(localized: "growth_goal_subtitle"))
                .font(.subheadline).foregroundStyle(.secondary)
            ForEach(options, id: \.0) { option in
                Button {
                    selection = option.0
                } label: {
                    HStack(spacing: 14) {
                        Image(systemName: option.2).frame(width: 24)
                        Text(String(localized: String.LocalizationValue(option.1)))
                        Spacer()
                        Image(systemName: selection == option.0 ? "checkmark.circle.fill" : "circle")
                    }
                    .padding(18)
                    .foregroundStyle(AppTheme.Colors.label)
                    .background(selection == option.0 ? InitialExperienceStyle.accent.opacity(0.12) : AppTheme.Colors.cardBackground.opacity(0.8))
                    .clipShape(RoundedRectangle(cornerRadius: 16))
                    .overlay(RoundedRectangle(cornerRadius: 16).strokeBorder(selection == option.0 ? InitialExperienceStyle.accent : .clear))
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("onboarding-goal-\(option.0)")
                .accessibilityAddTraits(selection == option.0 ? .isSelected : [])
            }
            Spacer(minLength: 12)
            VStack(alignment: .leading, spacing: 8) {
                Text(String(localized: "growth_name_title"))
                    .font(.subheadline).foregroundStyle(.secondary)
                TextField(String(localized: "growth_name_placeholder"), text: $name)
                    .textFieldStyle(.roundedBorder)
                    .textInputAutocapitalization(.words)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("onboarding-name-field")
            }
            Button {
                var profile = appState.userProfile
                profile.goals = [selection]
                appState.updateUserProfile(profile, sync: true)
                // Phase 1: desired state + optional name land in the
                // personalization profile. The name is trimmed, empty
                // becomes nil, and it never leaves the device.
                var personalization = appState.personalizationProfile
                personalization.desiredState = selection
                let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
                personalization.preferredName = trimmed.isEmpty ? nil : trimmed
                appState.updatePersonalizationProfile(personalization)
                next()
            } label: {
                Text(String(localized: "growth_find_words"))
                    .font(.headline).frame(maxWidth: .infinity).padding(18)
                    .foregroundStyle(.white).background(InitialExperienceStyle.accent)
                    .clipShape(RoundedRectangle(cornerRadius: 18))
            }
            .accessibilityIdentifier("onboarding-goal-continue")
            .padding(.bottom, 24)
        }
        .padding(.horizontal, 24)
        .foregroundStyle(AppTheme.Colors.label)
        .background(InitialExperienceStyle.background)
        .onAppear {
            selection = appState.personalizationProfile.desiredState.flatMap { value in options.contains(where: { $0.0 == value }) ? value : nil }
                ?? appState.userProfile.goals.first.flatMap { value in options.contains(where: { $0.0 == value }) ? value : nil } ?? "self_love"
            name = appState.personalizationProfile.preferredName ?? ""
        }
    }
}

struct FirstAffirmationStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState
    @StateObject private var likedStore = LikedQuotesStore()
    @State private var selection: PersonalizedNudgeSelector.Selection?
    @State private var didRecordDecision = false

    /// Legacy goal→quote map, kept as the fallback for profiles without
    /// Phase 1 answers (e.g. a resumed pre-Phase-1 onboarding).
    private var legacyQuote: Quote {
        let quoteIDs = ["self_love": "q013", "calm": "q021", "confidence": "q041", "letting_go": "q071"]
        let id = quoteIDs[appState.userProfile.goals.first ?? "self_love"] ?? "q013"
        return QuoteProvider.shared.byId(id, preferredLanguage: appState.effectiveLanguage)
            ?? QuoteProvider.shared.all(preferredLanguage: appState.effectiveLanguage)[0]
    }

    private var quote: Quote { selection?.quote ?? legacyQuote }

    private func computeSelectionIfNeeded() {
        guard selection == nil else { return }
        let profile = appState.personalizationProfile
        guard profile.hasAnswers else { return }
        let band = PersonalizedNudgeSelector.TimeBand.band(
            forHour: Calendar.current.component(.hour, from: Date())
        )
        selection = PersonalizedNudgeSelector.select(
            profile: profile,
            pool: QuoteProvider.shared.all(preferredLanguage: appState.effectiveLanguage),
            shownAt: DecisionPointStore.shared.shownTimestamps(),
            band: band
        )
        if let selection, !didRecordDecision {
            didRecordDecision = true
            DecisionPointRecorder.shared.recordDecision(
                selection: selection,
                profile: profile,
                source: "onboarding_preview"
            )
        }
    }

    var body: some View {
        VStack(spacing: 24) {
            Text("Anicca").font(.system(size: 28, design: .serif)).padding(.top, 20)
            Spacer(minLength: 16)
            Image(systemName: "sun.max")
                .font(.system(size: 46, weight: .ultraLight))
                .foregroundStyle(InitialExperienceStyle.accent)
                .padding(24)
                .background(Circle().fill(AppTheme.Colors.habitAccent.opacity(0.2)))
                .accessibilityHidden(true)
            Text(String(localized: "growth_first_affirmation")).font(.caption).tracking(2).foregroundStyle(.secondary)
            if let name = appState.personalizationProfile.preferredName {
                Text(String(format: NSLocalizedString("growth_first_for_name", comment: ""), name))
                    .font(.subheadline).foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            Text(quote.text)
                .font(.system(.largeTitle, design: .serif))
                .multilineTextAlignment(.center).fixedSize(horizontal: false, vertical: true)
                .accessibilityIdentifier("onboarding-first-affirmation")
            Text(String(localized: "growth_first_subtitle"))
                .font(.subheadline).foregroundStyle(.secondary).multilineTextAlignment(.center)
            Button {
                let liked = likedStore.toggle(quote)
                AnalyticsManager.shared.track(liked ? .affirmationLiked : .affirmationUnliked, properties: ["quote_id": quote.id, "category": quote.categoryID, "source": "onboarding"])
            } label: {
                Label(String(localized: likedStore.isLiked(quote.id) ? "growth_saved" : "growth_keep_close"),
                      systemImage: likedStore.isLiked(quote.id) ? "heart.fill" : "heart")
                    .font(.subheadline).padding(14)
                    .background(AppTheme.Colors.cardBackground.opacity(0.8))
                    .clipShape(Capsule())
            }
            .buttonStyle(.plain)
            .accessibilityIdentifier("onboarding-first-save")
            Spacer(minLength: 16)
            Button(action: next) {
                Text(String(localized: "growth_daily_moment"))
                    .font(.headline).frame(maxWidth: .infinity).padding(18)
                    .foregroundStyle(.white).background(InitialExperienceStyle.accent)
                    .clipShape(RoundedRectangle(cornerRadius: 18))
            }
            .accessibilityIdentifier("onboarding-first-continue")
            .padding(.bottom, 24)
        }
        .padding(.horizontal, 24)
        .foregroundStyle(AppTheme.Colors.label)
        .background(InitialExperienceStyle.background)
        .onAppear {
            computeSelectionIfNeeded()
            AnalyticsManager.shared.track(.firstAffirmationViewed, properties: ["quote_id": quote.id, "category": quote.categoryID])
        }
    }
}

/// Phase 1: the reminder schedule is chosen by the user, not just shown.
/// Slots (1–3 of the presets) and the daily frequency are persisted in the
/// personalization profile and synced; the struggle-frequency answer only
/// sets the initial proposal. Explicit choices always win.
struct ReminderScheduleStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState
    @State private var selectedSlots: Set<NudgeSlot> = []
    @State private var frequency: Int = 1
    @State private var didInitialize = false

    private var sortedSlots: [NudgeSlot] { selectedSlots.sorted() }
    private var isValid: Bool {
        PersonalizationRules.isValidSchedule(slots: sortedSlots, frequency: frequency)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            Text("Anicca").font(.system(size: 28, design: .serif)).padding(.top, 20)
            Image(systemName: "bell.badge").font(.system(size: 40, weight: .ultraLight)).foregroundStyle(InitialExperienceStyle.accent)
                .accessibilityHidden(true)
            Text(String(localized: "growth_reminder_title")).font(.system(.largeTitle, design: .serif))
            Text(String(localized: "growth_reminder_explanation")).font(.subheadline).foregroundStyle(.secondary)

            VStack(alignment: .leading, spacing: 10) {
                Text(String(localized: "growth_slots_title")).font(.headline)
                ForEach(PersonalizationRules.presetSlots, id: \.self) { slot in
                    Button {
                        toggle(slot)
                    } label: {
                        HStack(spacing: 14) {
                            Text(slot.label)
                            Spacer()
                            Image(systemName: selectedSlots.contains(slot) ? "checkmark.circle.fill" : "circle")
                        }
                        .padding(14)
                        .foregroundStyle(AppTheme.Colors.label)
                        .background(selectedSlots.contains(slot) ? InitialExperienceStyle.accent.opacity(0.12) : AppTheme.Colors.cardBackground.opacity(0.8))
                        .clipShape(RoundedRectangle(cornerRadius: 14))
                    }
                    .buttonStyle(.plain)
                    .accessibilityIdentifier("onboarding-slot-\(slot.hour)")
                }
            }

            VStack(alignment: .leading, spacing: 10) {
                Text(String(localized: "growth_frequency_title")).font(.headline)
                HStack(spacing: 10) {
                    ForEach(1...PersonalizationRules.freeFrequencyCap, id: \.self) { count in
                        Button {
                            frequency = count
                        } label: {
                            Text("\(count)")
                                .font(.headline)
                                .frame(maxWidth: .infinity)
                                .padding(14)
                                .foregroundStyle(frequency == count ? .white : AppTheme.Colors.label)
                                .background(frequency == count ? InitialExperienceStyle.accent : AppTheme.Colors.cardBackground.opacity(0.8))
                                .clipShape(RoundedRectangle(cornerRadius: 14))
                        }
                        .buttonStyle(.plain)
                        .accessibilityIdentifier("onboarding-frequency-\(count)")
                    }
                }
                if frequency > selectedSlots.count {
                    Text(String(localized: "growth_slots_need_more"))
                        .font(.caption).foregroundStyle(.secondary)
                }
            }

            Text(TimeZone.current.identifier).font(.caption).foregroundStyle(.secondary)
            Spacer()
            Button {
                save()
                next()
            } label: {
                Text(String(localized: "common_continue")).font(.headline)
                    .frame(maxWidth: .infinity).padding(18)
                    .foregroundStyle(.white).background(isValid ? InitialExperienceStyle.accent : InitialExperienceStyle.accent.opacity(0.4))
                    .clipShape(RoundedRectangle(cornerRadius: 18))
            }
            .disabled(!isValid)
            .accessibilityIdentifier("onboarding-reminder-continue")
            .padding(.bottom, 24)
        }
        .padding(.horizontal, 24).foregroundStyle(AppTheme.Colors.label)
        .background(InitialExperienceStyle.background)
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
            // A saved explicit choice always wins over any proposal.
            selectedSlots = Set(profile.nudgeSlots)
            frequency = profile.dailyFrequency
        } else {
            frequency = PersonalizationRules.proposedFrequency(struggleFrequency: profile.struggleFrequency)
            selectedSlots = Set(PersonalizationRules.proposedSlots(
                painPointIds: profile.painPointIds,
                frequency: frequency
            ))
        }
    }

    private func save() {
        var profile = appState.personalizationProfile
        profile.nudgeSlots = sortedSlots
        profile.dailyFrequency = frequency
        appState.updatePersonalizationProfile(profile)
    }
}

/// The first personalized intervention, shown after the soft paywall —
/// whether the user purchased or closed the paywall (mapping rule 5).
/// Selected from the same profile by the same rule as the preview, and
/// recorded as its own decision point.
struct FirstInterventionStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState
    @State private var selection: PersonalizedNudgeSelector.Selection?
    @State private var didRecordDecision = false

    private var quote: Quote? { selection?.quote }

    private var nextSlotLabel: String? {
        let slots = appState.personalizationProfile.nudgeSlots
        guard let first = slots.sorted().first else { return nil }
        return first.label
    }

    var body: some View {
        VStack(spacing: 24) {
            Text("Anicca").font(.system(size: 28, design: .serif)).padding(.top, 20)
            Spacer(minLength: 16)
            Image(systemName: "sun.max")
                .font(.system(size: 46, weight: .ultraLight))
                .foregroundStyle(InitialExperienceStyle.accent)
                .padding(24)
                .background(Circle().fill(AppTheme.Colors.habitAccent.opacity(0.2)))
                .accessibilityHidden(true)
            Text(String(localized: "growth_first_affirmation")).font(.caption).tracking(2).foregroundStyle(.secondary)
            if let name = appState.personalizationProfile.preferredName {
                Text(String(format: NSLocalizedString("growth_first_for_name", comment: ""), name))
                    .font(.subheadline).foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            if let quote {
                Text(quote.text)
                    .font(.system(.largeTitle, design: .serif))
                    .multilineTextAlignment(.center).fixedSize(horizontal: false, vertical: true)
                    .accessibilityIdentifier("onboarding-first-intervention")
            }
            if let nextSlotLabel {
                Text(String(format: NSLocalizedString("growth_first_next_time", comment: ""), nextSlotLabel))
                    .font(.subheadline).foregroundStyle(.secondary).multilineTextAlignment(.center)
            }
            Spacer(minLength: 16)
            Button(action: next) {
                Text(String(localized: "growth_daily_moment"))
                    .font(.headline).frame(maxWidth: .infinity).padding(18)
                    .foregroundStyle(.white).background(InitialExperienceStyle.accent)
                    .clipShape(RoundedRectangle(cornerRadius: 18))
            }
            .accessibilityIdentifier("onboarding-intervention-continue")
            .padding(.bottom, 24)
        }
        .padding(.horizontal, 24)
        .foregroundStyle(AppTheme.Colors.label)
        .background(InitialExperienceStyle.background)
        .onAppear { computeSelectionIfNeeded() }
    }

    private func computeSelectionIfNeeded() {
        guard selection == nil else { return }
        let profile = appState.personalizationProfile
        let band = PersonalizedNudgeSelector.TimeBand.band(
            forHour: Calendar.current.component(.hour, from: Date())
        )
        selection = PersonalizedNudgeSelector.select(
            profile: profile,
            pool: QuoteProvider.shared.all(preferredLanguage: appState.effectiveLanguage),
            shownAt: DecisionPointStore.shared.shownTimestamps(),
            band: band
        )
        if let selection, !didRecordDecision {
            didRecordDecision = true
            DecisionPointRecorder.shared.recordDecision(
                selection: selection,
                profile: profile,
                source: "onboarding_first_intervention"
            )
            AnalyticsManager.shared.track(.firstAffirmationViewed, properties: [
                "quote_id": selection.quote.id,
                "category": selection.quote.categoryID,
                "source": "first_intervention",
            ])
        }
    }
}
