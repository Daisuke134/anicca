import SwiftUI
import RevenueCat
import RevenueCatUI
import UserNotifications

/// Onboarding: questions → personalized preview → soft paywall → first
/// personalized intervention → free feed. Completing never depends on a
/// purchase; the paywall is closable and the intervention is shown either way.
struct OnboardingFlowView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.scenePhase) private var scenePhase
    @State private var step: OnboardingStep = .welcome
    @State private var lastTrackedStep: OnboardingStep?
    @State private var didTrackOnboardingStart = false
    @State private var showPaywall = false
    @State private var showFirstIntervention = false
    @State private var showRatingPrompt = false

    var body: some View {
        ZStack {
            AppBackground()

            VStack(spacing: 0) {
                OnboardingProgressBar(step: step, journey: journey)
                    .padding(.horizontal, 16)
                    .padding(.top, 8)

                Group {
                    onboardingContent(for: step)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }

        }
        .onAppear {
            if appState.onboardingQuestionsCompleted {
                completeFreeOnboarding()
                return
            }

            step = appState.onboardingStep.resumableStep(
                painPointIds: appState.personalizationProfile.painPointIds,
                priorAttempts: appState.personalizationProfile.answers.ids(for: .priorAttempts))
            if !didTrackOnboardingStart {
                didTrackOnboardingStart = true
                AnalyticsManager.shared.track(.onboardingStarted, properties: [
                    "entry_screen_id": AnalyticsScreenID.onboarding(step).rawValue,
                    "resumed": step != .welcome,
                    "flow_id": "onboarding",
                ])
            }
            recordStepView()

            Task {
                await SubscriptionManager.shared.refreshOfferings()
            }
        }
        .onChange(of: step) { _ in recordStepView() }
        // Abandonment: leaving for the background with questions
        // unfinished fixes the step the person left at. AppDelegate's
        // applicationDidEnterBackground fires the same tracker for the
        // same transition; the tracker dedupes it to one event.
        .onChange(of: scenePhase) { phase in
            if phase == .background, !appState.onboardingQuestionsCompleted, !appState.isOnboardingComplete {
                AnalyticsManager.shared.trackOnboardingAbandonedIfNeeded()
            }
        }
        // Phase 1 ending: after the questions, show the soft paywall, then
        // the first personalized intervention — whether the user purchases
        // or closes the paywall — and only then complete into the feed.
        .fullScreenCover(isPresented: $showPaywall) {
            PaywallFlowContainer(
                onPurchaseSuccess: { _ in
                    showPaywall = false
                    showFirstIntervention = true
                },
                onDismiss: {
                    showPaywall = false
                    showFirstIntervention = true
                }
            )
            .environmentObject(appState)
        }
        .fullScreenCover(isPresented: $showFirstIntervention) {
            FirstInterventionStepView(next: {
                showFirstIntervention = false
                showRatingPrompt = true
            })
            .environmentObject(appState)
        }
        // The review step closes onboarding: after the value moment
        // (the first personalized words above), never at first launch.
        // See RatingPrePromptStepView for the placement reasoning.
        .fullScreenCover(isPresented: $showRatingPrompt) {
            RatingPrePromptStepView(next: {
                showRatingPrompt = false
                completeFreeOnboarding()
            })
        }
    }

    private var journey: [OnboardingStep] {
        OnboardingStep.journey(painPointIds: appState.personalizationProfile.painPointIds,
                               priorAttempts: appState.personalizationProfile.answers.ids(for: .priorAttempts))
    }

    // MARK: - Onboarding Steps

    @ViewBuilder
    private func onboardingContent(for step: OnboardingStep) -> some View {
        switch step {
        case .welcome:          WelcomeStepView(next: advance)
        case .goal:             AffirmationGoalStepView(next: advance)
        case .name:             PreferredNameStepView(next: advance)
        case .birthContext: AdaptiveQuestionStepView(question: .birthContext, next: advance).id(step)
        case .moodBaseline: AdaptiveQuestionStepView(question: .moodBaseline, next: advance).id(step)
        case .beliefThemes: AdaptiveQuestionStepView(question: .beliefThemes, next: advance).id(step)
        case .tone: AdaptiveQuestionStepView(question: .tone, next: advance).id(step)
        case .lifeContext: AdaptiveQuestionStepView(question: .lifeContext, next: advance).id(step)
        case .routineAnchors: AdaptiveQuestionStepView(question: .routineAnchors, next: advance).id(step)
        case .priorAttempts: AdaptiveQuestionStepView(question: .priorAttempts, next: advance).id(step)
        case .startReason: AdaptiveQuestionStepView(question: .startReason, next: advance).id(step)
        case .quietHours: AdaptiveQuestionStepView(question: .quietHours, next: advance).id(step)
        case .stressTrigger: AdaptiveQuestionStepView(question: .stressTrigger, next: advance).id(step)
        case .anxietyTarget: AdaptiveQuestionStepView(question: .anxietyTarget, next: advance).id(step)
        case .selfCriticism: AdaptiveQuestionStepView(question: .selfCriticism, next: advance).id(step)
        case .avoidanceTask: AdaptiveQuestionStepView(question: .avoidanceTask, next: advance).id(step)
        case .sleepReason: AdaptiveQuestionStepView(question: .sleepReason, next: advance).id(step)
        case .bedtime: AdaptiveQuestionStepView(question: .bedtime, next: advance).id(step)
        case .wakeTime: AdaptiveQuestionStepView(question: .wakeTime, next: advance).id(step)
        case .priorHelpfulness: AdaptiveQuestionStepView(question: .priorHelpfulness, next: advance).id(step)
        case .painPoints:       StrugglesStepView(next: advance)
        case .struggleFreq:     StruggleDepthStepView(next: advance)
        case .nudgeTimes:       ReminderScheduleStepView(next: advance)
        case .planReveal:       FirstAffirmationStepView(next: advance)
        case .processing, .comparison: FirstAffirmationStepView(next: advance)
        case .notifications:    NotificationPermissionStepView(next: advance)
        }
    }

    // MARK: - Navigation

    private func recordStepView() {
        guard lastTrackedStep != step else { return }
        lastTrackedStep = step
        let screenID = AnalyticsScreenID.onboarding(step)
        AnalyticsManager.shared.trackScreenViewedIfNeeded(screenID: screenID, flowID: "onboarding")
        AnalyticsManager.shared.noteOnboardingStepViewed(step: step, flowID: "onboarding")
        AnalyticsManager.shared.track(.onboardingStepViewed, properties: [
            "screen_id": screenID.rawValue,
            "step_index": step.rawValue,
            "flow_id": "onboarding",
        ])
    }

    private func advance() {
        // The completing step's view saved its answer into
        // personalizationProfile before calling next(), so this event
        // carries that answer as answer_ids (+ user property).
        AnalyticsManager.shared.trackOnboardingStepCompleted(
            step: step, profile: appState.personalizationProfile)

        if step == .notifications {
            appState.markOnboardingQuestionsCompleted()
            AnalyticsManager.shared.track(.onboardingCompleted)
            AnalyticsManager.shared.updateSKANConversionValue(1)
            presentPaywallOnlyIfNotSubscribed()
            return
        }

        if let next = step.nextStep(
            painPointIds: appState.personalizationProfile.painPointIds,
            priorAttempts: appState.personalizationProfile.answers.ids(for: .priorAttempts)) {
            AnalyticsManager.shared.trackScreenExited(nextScreenID: AnalyticsScreenID.onboarding(next).rawValue)
            step = next
            appState.setOnboardingStep(step)
        }
    }

    /// The paywall is for non-subscribers only (user rule, 2026-11-15):
    /// a user whose entitlement is already active goes straight to the
    /// first intervention and never sees a purchase screen. The
    /// entitlement is refreshed live first, so a subscription started on
    /// another device is honored; the decision itself lives in
    /// PaywallPresentationPolicy so every entry point agrees.
    private func presentPaywallOnlyIfNotSubscribed() {
        Task {
            let refreshed = await SubscriptionManager.shared.refreshCustomerInfo()
            if PaywallPresentationPolicy.shouldPresent(
                refreshedIsEntitled: refreshed,
                cachedIsEntitled: appState.subscriptionInfo.isEntitled) {
                showPaywall = true
            } else {
                showFirstIntervention = true
            }
        }
    }

    private func completeFreeOnboarding() {
        AnalyticsManager.shared.trackScreenExited(nextScreenID: AnalyticsScreenID.feed.rawValue)
        appState.markOnboardingComplete()
    }
}
