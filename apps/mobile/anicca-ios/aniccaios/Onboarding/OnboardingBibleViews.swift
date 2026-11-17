import SwiftUI
import StoreKit
import RevenueCat

// MARK: - Rating Pre-Prompt (restored 2026-11-15)

/// The in-onboarding review step, restored on the user's direct order:
/// this form earned 48 App Store reviews and its removal (ca146d243,
/// replaced by a 3-open-day policy) is superseded. Placement is the
/// compliance-critical part: never on the first screen — Honne 1.0.7
/// was rejected under Guideline 5.6.3 for asking at first launch — but
/// inside onboarding, immediately after the value moment (the first
/// personalized words). OnboardingFlowView presents it after the first
/// intervention and before the feed.
struct RatingPrePromptStepView: View {
    let next: () -> Void
    @State private var awaitingReview = false

    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            Text(String(localized: "onboarding_rating_title"))
                .font(.system(size: 28, weight: .bold))
                .multilineTextAlignment(.center)
                .foregroundStyle(AppTheme.Colors.label)
                .padding(.horizontal, 24)

            HStack(spacing: 4) {
                ForEach(0..<5) { _ in
                    Image(systemName: "star.fill")
                        .font(.system(size: 36))
                        .foregroundStyle(.yellow)
                }
            }

            Spacer()

            Button {
                AnalyticsManager.shared.track(.ratingPromptYesTapped)
                requestStoreReview()
            } label: {
                Text(String(localized: "rating_cta"))
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity).frame(height: 56)
                    .background(AppTheme.Colors.accent)
                    .clipShape(RoundedRectangle(cornerRadius: 28))
            }
            .accessibilityIdentifier("onboarding-rating-continue")
            .padding(.horizontal, 24)
            .padding(.bottom, 48)
        }
        .background(AppBackground())
        .onAppear { AnalyticsManager.shared.track(.ratingPromptShown) }
        .onReceive(NotificationCenter.default.publisher(
            for: UIApplication.didBecomeActiveNotification
        )) { _ in
            if awaitingReview {
                awaitingReview = false
                next()
            }
        }
    }

    private func requestStoreReview() {
        let launchArguments = ProcessInfo.processInfo.arguments
        // UI tests verify the step itself; the system dialog is Apple's
        // and cannot be driven by Maestro. "-uiTesting" is the living-
        // home E2E convention; the historical checks are kept alongside.
        if launchArguments.contains("UITESTING") || launchArguments.contains("-UITESTING")
            || launchArguments.contains("-uiTesting") {
            next()
            return
        }

        AnalyticsManager.shared.track(.ratingStoreReviewRequested)
        awaitingReview = true
        if let scene = UIApplication.shared.connectedScenes
            .first(where: { $0.activationState == .foregroundActive }) as? UIWindowScene {
            SKStoreReviewController.requestReview(in: scene)
        }
        // Fallback: system may suppress dialog (3x/year limit) or simulator
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            if self.awaitingReview {
                self.awaitingReview = false
                self.next()
            }
        }
    }
}

// MARK: - Optional Paywall

struct PaywallFlowContainer: View {
    let onPurchaseSuccess: (CustomerInfo) -> Void
    let onDismiss: () -> Void
    var flowID: String = "onboarding"
    @State private var step: PaywallStep = .planSelection
    @EnvironmentObject private var appState: AppState

    var body: some View {
        ZStack(alignment: .topTrailing) {
            AppBackground()

            switch step {
            case .primer:
                PaywallPrimerStepView(next: { step = .planSelection })
                    .transition(.opacity)
            case .planSelection:
                PaywallVariantBView(
                    variant: "b",
                    onPurchaseSuccess: onPurchaseSuccess,
                    onDismiss: onDismiss,
                    flowID: flowID
                )
                .transition(.opacity)
            }

            Group {
                Button(action: onDismiss) {
                    Image(systemName: "xmark")
                        .font(.system(size: 17, weight: .semibold))
                        .foregroundStyle(.secondary)
                        .frame(width: 44, height: 44)
                        .contentShape(Rectangle())
                }
                .buttonStyle(PressScaleButtonStyle())
                .accessibilityIdentifier("paywall-close-button")
                .accessibilityLabel(Text(String(localized: "common_close")))
                .padding(.trailing, 12)
                .padding(.top, 8)
            }
        }
        // Primer -> plan selection is on-screen movement: cross-fade with
        // the shared motion token instead of teleporting (AUDIT §8).
        .animation(AppMotion.move, value: step)
        .analyticsScreen(.paywall, flowID: flowID)
    }
}
