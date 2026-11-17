import SwiftUI
import RevenueCat
import RevenueCatUI
import UserNotifications
import StoreKit

/// Adaptive questions, first intervention, optional purchase, then the free feed.
struct OnboardingFlowView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var step: OnboardingStep = .welcome
    @State private var lastTrackedStep: OnboardingStep?
    @State private var didTrackOnboardingStart = false
    @Environment(\.requestReview) private var requestReview
    @AppStorage("onboarding.winner.startedAt") private var startedAt = 0.0
    @AppStorage("onboarding.winner.reviewRequested") private var reviewRequested = false
    @State private var checkingEntitlement = false
    @State private var paywallReady = false

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
                .id(step)
                .transition(stepTransition)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }

        }
        .animation(stepAnimation, value: step)
        .onAppear {
            if startedAt == 0 { startedAt = Date().timeIntervalSince1970 }
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

    }

    /// Step changes are on-screen movement, so they take the shared
    /// ease-in-out motion token; under Reduce Motion they collapse to a
    /// cross-fade (improve-animations AUDIT §2/§6; apple-design §14).
    private var stepAnimation: Animation {
        reduceMotion ? .easeInOut(duration: 0.2) : AppMotion.move
    }

    private var stepTransition: AnyTransition {
        reduceMotion
            ? .opacity
            : .asymmetric(
                insertion: .move(edge: .trailing).combined(with: .opacity),
                removal: .move(edge: .leading).combined(with: .opacity))
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
        case .focusCategories: AdaptiveQuestionStepView(question: .focusCategories, next: advance).id(step)
        case .microPreview: MicroPreviewStepView(next: advance)
        case .themeChoice: OnboardingThemeStepView(next: advance)
        case .iconChoice: OnboardingIconStepView(next: advance)
        case .widgetPreview: OnboardingWidgetStepView(next: advance)
        case .paywall:
            Group {
                if paywallReady {
                    PaywallFlowContainer(onPurchaseSuccess: { _ in advance() }, onDismiss: advance)
                        .onAppear {
                            AnalyticsManager.shared.track(.onboardingPaywallArrived, properties: [
                                "elapsed_seconds": max(0, Date().timeIntervalSince1970 - startedAt),
                                "screen_count": journey.count, "flow_id": "onboarding"
                            ])
                        }
                } else { ProgressView() }
            }
            .task {
                guard !checkingEntitlement else { return }
                checkingEntitlement = true
                let refreshed = await SubscriptionManager.shared.refreshCustomerInfo()
                guard self.step == .paywall, !appState.isOnboardingComplete else { return }
                if PaywallPresentationPolicy.shouldPresent(refreshedIsEntitled: refreshed,
                    cachedIsEntitled: appState.subscriptionInfo.isEntitled) { paywallReady = true }
                else { advance() }
            }
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
        guard !appState.isOnboardingComplete else { return }
        // The completing step's view saved its answer into
        // personalizationProfile before calling next(), so this event
        // carries that answer as answer_ids (+ user property).
        AnalyticsManager.shared.trackOnboardingStepCompleted(
            step: step, profile: appState.personalizationProfile)

        if step == .planReveal, !reviewRequested {
            reviewRequested = true
            let arguments = ProcessInfo.processInfo.arguments
            if !["-uiTesting", "UITESTING", "-UITESTING"].contains(where: arguments.contains) {
                appState.markReviewRequested()
                AnalyticsManager.shared.track(.ratingStoreReviewRequested)
                requestReview()
            }
        }

        if step == .paywall {
            appState.markOnboardingQuestionsCompleted()
            AnalyticsManager.shared.track(.onboardingCompleted)
            AnalyticsManager.shared.updateSKANConversionValue(1)
            completeFreeOnboarding()
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

    private func completeFreeOnboarding() {
        AnalyticsManager.shared.trackScreenExited(nextScreenID: AnalyticsScreenID.feed.rawValue)
        appState.markOnboardingComplete()
        startedAt = 0
    }
}
