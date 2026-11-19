import SwiftUI
import UIKit

struct MicroPreviewStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState
    @StateObject private var likedStore = LikedQuotesStore()
    @State private var quote: Quote?
    @State private var deliveryID: String?

    var body: some View {
        OnboardingPage {
            Text(String(localized: "winner_micro_title")).font(AppTheme.Typography.onboardingTitle)
            if let quote {
                Text([appState.personalizationProfile.preferredName, quote.text].compactMap { $0 }.joined(separator: ", "))
                    .font(.system(.title2, design: .serif))
                    .multilineTextAlignment(.center)
                    .accessibilityIdentifier("onboarding-micro-preview")
            }
        } footer: {
            VStack(spacing: 12) {
                PrimaryButton(title: String(localized: "growth_keep_close"), isEnabled: quote != nil) { finish(saved: true) }
                    .accessibilityIdentifier("onboarding-micro-save")
                Button { finish(saved: false) } label: {
                    Text(String(localized: "adaptive_skip"))
                        .frame(maxWidth: .infinity, minHeight: 44)
                        .contentShape(Rectangle())
                }
                    .buttonStyle(PressScaleButtonStyle())
                    .accessibilityIdentifier("onboarding-micro-skip")
            }
        }
        .onAppear {
            guard quote == nil else { return }
            let user = appState.syntheticUser
            let theme = user.beliefThemes.first
            let pool = QuoteProvider.shared.all(preferredLanguage: appState.effectiveLanguage)
            let matching = pool.filter {
                guard let traits = AdaptiveAffirmationCatalog.traits(for: $0) else { return false }
                return traits.tone == "gentle" && traits.intensity == "gentle" && !traits.fearBased
                    && traits.contexts.isEmpty && traits.answerMatches.isEmpty && traits.methods.isEmpty
                    && traits.beliefThemes.contains(theme ?? "inner_peace")
            }
            // All five belief themes have a gentle, context-free catalog sentence.
            guard let chosen = matching.sorted(by: { $0.id < $1.id }).first else { return }
            quote = chosen
            let selection = PersonalizedNudgeSelector.Selection(quote: chosen, reason: "micro_belief_preview",
                candidateCount: 1, candidateIDs: [chosen.id], assignedProbability: 1, policyVersion: "micro_preview_v1")
            deliveryID = DecisionPointRecorder.shared.recordDecision(selection: selection, syntheticUser: user, source: "onboarding_micro_preview")
        }
    }

    private func finish(saved: Bool) {
        if saved, let quote, !likedStore.isLiked(quote.id) {
            _ = likedStore.toggle(quote, themeID: ThemeStore().selected.rawValue)
        }
        if let deliveryID { DecisionPointRecorder.shared.recordResponse(deliveryId: deliveryID, event: saved ? .saved : .skipped) }
        var profile = appState.personalizationProfile
        var answers = profile.answers
        answers.set(.microPreview, ids: [saved ? "saved" : "skipped"])
        profile.adaptiveAnswers = answers
        appState.updatePersonalizationProfile(profile)
        next()
    }
}

struct OnboardingThemeStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState
    @StateObject private var themeStore = ThemeStore()

    var body: some View {
        VStack {
            Text(String(localized: "winner_theme_title")).font(AppTheme.Typography.onboardingTitle).padding()
            ThemePickerView(onboarding: true).environmentObject(themeStore)
            PrimaryButton(title: String(localized: "common_continue")) {
                var profile = appState.personalizationProfile
                var answers = profile.answers
                answers.set(.themeChoice, ids: [themeStore.selected.rawValue])
                profile.adaptiveAnswers = answers
                appState.updatePersonalizationProfile(profile)
                next()
            }.padding().accessibilityIdentifier("onboarding-theme-continue")
        }
    }
}

struct OnboardingIconStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState
    @State private var selected = UIApplication.shared.alternateIconName ?? "AppIcon"
    @State private var applying = false
    @State private var failed = false

    var body: some View {
        OnboardingPage {
            Text(String(localized: "winner_icon_title")).font(AppTheme.Typography.onboardingTitle)
            ForEach(OnboardingQuestion.iconChoice.optionIDs, id: \.self) { id in
                Button { UISelectionFeedbackGenerator().selectionChanged(); selected = id; failed = false } label: {
                    HStack {
                        Image("Preview\(id)").resizable().frame(width: 64, height: 64).clipShape(RoundedRectangle(cornerRadius: 14))
                        Text(NSLocalizedString("winner_icon_\(id)", comment: ""))
                        Spacer()
                        Image(systemName: selected == id ? "checkmark.circle.fill" : "circle")
                    }.padding(12).selectionCard(isSelected: selected == id)
                    .contentShape(Rectangle())
                }.buttonStyle(.plain).accessibilityIdentifier("onboarding-icon-\(id)")
            }
            if failed { Text(String(localized: "winner_icon_error")).foregroundStyle(.secondary) }
        } footer: {
            VStack(spacing: 12) {
                PrimaryButton(title: String(localized: "common_continue"), isEnabled: !applying) { apply() }
                    .accessibilityIdentifier("onboarding-icon-continue")
                if failed {
                    Button { save(UIApplication.shared.alternateIconName ?? "AppIcon") } label: {
                        Text(String(localized: "adaptive_skip"))
                            .frame(maxWidth: .infinity, minHeight: 44)
                            .contentShape(Rectangle())
                    }
                }
            }
        }
    }

    private func apply() {
        let current = UIApplication.shared.alternateIconName ?? "AppIcon"
        guard selected != current else { save(current); return }
        guard UIApplication.shared.supportsAlternateIcons else { failed = true; return }
        applying = true
        UIApplication.shared.setAlternateIconName(selected == "AppIcon" ? nil : selected) { error in
            DispatchQueue.main.async {
                applying = false
                if error == nil { save(selected) } else { failed = true }
            }
        }
    }

    private func save(_ id: String) {
        var profile = appState.personalizationProfile
        var answers = profile.answers
        answers.set(.iconChoice, ids: [id])
        profile.adaptiveAnswers = answers
        appState.updatePersonalizationProfile(profile)
        next()
    }
}

struct OnboardingWidgetStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState
    @StateObject private var themeStore = ThemeStore()

    var body: some View {
        OnboardingPage {
            Text(String(localized: "winner_widget_title")).font(AppTheme.Typography.onboardingTitle)
            VStack(spacing: 20) {
                Label(String(localized: "winner_widget_lock"), systemImage: "lock")
                Text(String(localized: "winner_widget_words")).font(.caption).padding()
                    .overlay(Capsule().stroke(.secondary))
                Label(String(localized: "winner_widget_home"), systemImage: "house")
                Text(String(localized: "winner_widget_words")).font(.system(.title3, design: .serif))
                    .padding(24).frame(width: 180, height: 180)
                    .foregroundStyle(themeStore.selected.foregroundColor)
                    .background { themeStore.image.resizable().scaledToFill() }
                    .clipShape(RoundedRectangle(cornerRadius: 24))
            }.accessibilityIdentifier("onboarding-widget-preview")
            Text(String(localized: "winner_widget_instructions")).font(.subheadline)
        } footer: {
            VStack(spacing: 12) {
                PrimaryButton(title: String(localized: "winner_widget_add")) { finish("interested") }
                    .accessibilityIdentifier("onboarding-widget-interested")
                Button { finish("later") } label: {
                    Text(String(localized: "winner_widget_later"))
                        .frame(maxWidth: .infinity, minHeight: 44)
                        .contentShape(Rectangle())
                }
                    .buttonStyle(PressScaleButtonStyle())
                    .accessibilityIdentifier("onboarding-widget-later")
            }
        }
    }

    private func finish(_ id: String) {
        var profile = appState.personalizationProfile
        var answers = profile.answers
        answers.set(.widgetPreview, ids: [id])
        profile.adaptiveAnswers = answers
        appState.updatePersonalizationProfile(profile)
        next()
    }
}
