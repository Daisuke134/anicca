import SwiftUI
import RevenueCat
import RevenueCatUI
import UserNotifications

/// Goal → real affirmation → optional reminder settings → paywall.
/// Paywall presented via .fullScreenCover + .interactiveDismissDisabled (スワイプ離脱は防止)。
/// 2026-11-08 ハードペイウォール A/B 化: ゲートの形は RevenueCat Experiment の
/// 割当 Offering で決まる (PaywallGateVariant)。検証群 (hard) では × を表示せず
/// 購入成功か復元で entitled になるまで onboarding を完了させない。対照群
/// (soft) では従来どおり × で無料完了できる。
struct OnboardingFlowView: View {
    @EnvironmentObject private var appState: AppState
    @State private var step: OnboardingStep = .welcome
    @State private var showPaywall: Bool = false
    @State private var isResolvingPaywallEntry = false
    @State private var didPurchaseOnPaywall = false
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

            if isResolvingPaywallEntry {
                ProgressView()
                    .accessibilityIdentifier("onboarding-paywall-entitlement-check")
            }
        }
        .onAppear {
            if appState.onboardingQuestionsCompleted {
                resolveOnboardingPaywallEntry(source: "resume")
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
        .fullScreenCover(isPresented: $showPaywall) {
            PaywallFlowContainer(
                onPurchaseSuccess: { customerInfo in
                    handlePaywallSuccess(customerInfo: customerInfo)
                },
                onDismiss: {
                    if gateVariant == .soft {
                        handlePaywallDismissedAsFree()
                    } else {
                        handlePaywallDismissalBlocked()
                    }
                }
            )
            .environmentObject(appState)
            .interactiveDismissDisabled(true)
        }
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
            resolveOnboardingPaywallEntry(source: "completion")
            return
        }

        if let next = step.nextInitialStep {
            AnalyticsManager.shared.trackScreenExited(nextScreenID: AnalyticsScreenID.onboarding(next).rawValue)
            step = next
            appState.setOnboardingStep(step)
        }
    }

    private func completeOnboardingForExistingPro() {
        // v1.8.7: remote-only notifications. APNs registration is triggered on
        // permission grant and on app foreground — nothing to schedule locally.
        appState.markOnboardingComplete()
    }

    @MainActor
    private func resolveOnboardingPaywallEntry(source: String) {
        guard !isResolvingPaywallEntry else { return }
        isResolvingPaywallEntry = true
        Task { @MainActor in
            let freshEntitlement = await SubscriptionManager.shared.refreshCustomerInfo()
            let cachedEntitlement = appState.subscriptionInfo.isEntitled
            let result: String
            if let freshEntitlement {
                result = freshEntitlement ? "fresh_entitled" : "fresh_not_entitled"
            } else {
                result = cachedEntitlement ? "unavailable_cached_entitled" : "unavailable_cached_free"
            }
            AnalyticsManager.shared.track(.onboardingPaywallCustomerInfoResult, properties: [
                "source": source,
                "result": result,
                // A/B 露出計測: このユーザーに割り当てられたゲートを funnel で追う。
                "paywall_gate_variant": gateVariant.rawValue,
            ])

            let decision = OnboardingPaywallDecision.resolve(
                freshEntitlement: freshEntitlement,
                cachedEntitlement: cachedEntitlement
            )
            isResolvingPaywallEntry = false
            switch decision {
            case .completeOnboarding:
                AnalyticsManager.shared.trackScreenExited(nextScreenID: AnalyticsScreenID.feed.rawValue)
                completeOnboardingForExistingPro()
            case .presentPaywall:
                AnalyticsManager.shared.trackScreenExited(nextScreenID: AnalyticsScreenID.paywall.rawValue)
                showPaywall = true
            }
        }
    }

    private func handlePaywallSuccess(customerInfo: CustomerInfo) {
        AnalyticsManager.shared.trackScreenExited(nextScreenID: AnalyticsScreenID.feed.rawValue)
        didPurchaseOnPaywall = true
        appState.updateSubscriptionInfo(from: customerInfo)
        appState.markOnboardingComplete()
        showPaywall = false
    }

    /// このユーザーに割り当てられたペイウォールゲート (cachedOffering 由来)。
    private var gateVariant: PaywallGateVariant {
        PaywallGateVariant.resolve(offeringIdentifier: appState.cachedOffering?.identifier)
    }

    /// 対照群 (ソフトペイウォール): 右上 × で課金せずメイン画面へ。
    /// A/B の対照として 2026-11-08 に復活。検証群 (hard) では呼ばれない。
    private func handlePaywallDismissedAsFree() {
        AnalyticsManager.shared.trackScreenExited(nextScreenID: AnalyticsScreenID.feed.rawValue)
        AnalyticsManager.shared.track(.onboardingPaywallDismissedFree, properties: [
            "paywall_gate_variant": PaywallGateVariant.soft.rawValue,
        ])
        appState.markOnboardingComplete()
        showPaywall = false
    }

    /// 検証群 (ハードペイウォール): 新規導線では × を表示しないため通常は
    /// 呼ばれない。万一 dismiss が要求されても、購入成功
    /// (handlePaywallSuccess) か復元で entitled になるまで
    /// markOnboardingComplete を呼ばず、ペイウォールを表示したままにする。
    /// 離脱の計測は paywall_shown → purchase_started の funnel
    /// (paywall_gate_variant プロパティ付き) で追う。
    private func handlePaywallDismissalBlocked() {
        // Do not complete onboarding and do not dismiss the paywall.
        showPaywall = true
    }
}
