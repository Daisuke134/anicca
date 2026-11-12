import SwiftUI
import RevenueCat
import RevenueCatUI
import UserNotifications

/// Value-first onboarding completes into the free feed, independently of purchases or network.
struct OnboardingFlowView: View {
    @EnvironmentObject private var appState: AppState
    @State private var step: OnboardingStep = .welcome
    @State private var lastTrackedStep: OnboardingStep?
    @State private var didTrackOnboardingStart = false

    var body: some View {
        ZStack {
            AppBackground()

            VStack(spacing: 0) {
                OnboardingProgressBar(step: step)
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

            step = appState.onboardingStep.resumableInitialStep
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
    }

    // MARK: - Onboarding Steps

    @ViewBuilder
    private func onboardingContent(for step: OnboardingStep) -> some View {
        switch step {
        case .welcome:          WelcomeStepView(next: advance)
        case .goal:             AffirmationGoalStepView(next: advance)
        case .painPoints:       StrugglesStepView(next: advance)
        case .struggleFreq:     StruggleDepthStepView(next: advance)
        case .nudgeTimes:       ReminderScheduleStepView(next: advance)
        case .processing:       ProcessingStepView(next: advance)
        case .planReveal:       FirstAffirmationStepView(next: advance)
        case .comparison:       ComparisonTableStepView(next: advance)
        case .notifications:    NotificationPermissionStepView(next: advance)
        }
    }

    // MARK: - Navigation

    private func recordStepView() {
        guard lastTrackedStep != step else { return }
        lastTrackedStep = step
        let screenID = AnalyticsScreenID.onboarding(step)
        AnalyticsManager.shared.trackScreenViewedIfNeeded(screenID: screenID, flowID: "onboarding")
        AnalyticsManager.shared.track(.onboardingStepViewed, properties: [
            "screen_id": screenID.rawValue,
            "step_index": step.rawValue,
            "flow_id": "onboarding",
        ])
    }

    private func advance() {
        let screenID = AnalyticsScreenID.onboarding(step)
        AnalyticsManager.shared.track(.onboardingStepCompleted, properties: [
            "step_id": screenID.rawValue,
            "step_index": step.rawValue,
            "flow_id": "onboarding",
        ])

        if step == .notifications {
            appState.markOnboardingQuestionsCompleted()
            AnalyticsManager.shared.track(.onboardingCompleted)
            AnalyticsManager.shared.updateSKANConversionValue(1)
            completeFreeOnboarding()
            return
        }

        if let next = step.nextInitialStep {
            AnalyticsManager.shared.trackScreenExited(nextScreenID: AnalyticsScreenID.onboarding(next).rawValue)
            step = next
            appState.setOnboardingStep(step)
        }
    }

    private func completeFreeOnboarding() {
        AnalyticsManager.shared.trackScreenExited(nextScreenID: AnalyticsScreenID.feed.rawValue)
        appState.markOnboardingComplete()
    }
}
