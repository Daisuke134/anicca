import SwiftUI
import RevenueCat

struct PaywallView: View {
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    let isOnboarding: Bool
    @AppStorage("onboarding_completed") private var onboardingCompleted = false
    @Environment(\.presentationMode) var presentationMode
    @State private var selectedPlan: String = "annual"
    @State private var isLoading = false

    var body: some View {
        ZStack {
            Color(hex: "#0a1628").ignoresSafeArea()

            ScrollView {
                VStack(spacing: 24) {
                    Spacer().frame(height: 24)

                    // Headline
                    VStack(spacing: 8) {
                        Text(L10n.paywallHeadline)
                            .font(.system(size: 28, weight: .bold))
                            .foregroundColor(.white)
                            .multilineTextAlignment(.center)

                        Text(L10n.isJapaneseLang ?
                             "科学的根拠のある呼吸法で、神経系を\n60秒でリセット。" :
                             "Science-backed breathing resets your\nnervous system in 60 seconds.")
                            .font(.system(size: 15))
                            .foregroundColor(Color(hex: "#9ca3af"))
                            .multilineTextAlignment(.center)
                    }
                    .padding(.horizontal, 24)

                    // Feature comparison
                    VStack(spacing: 0) {
                        featureRow(
                            title: L10n.paywallFreeTitle,
                            desc: L10n.paywallFreeDesc,
                            isPro: false
                        )
                        Divider().background(Color(hex: "#1f2937"))
                        featureRow(
                            title: "✨ " + L10n.paywallProTitle,
                            desc: L10n.paywallProDesc,
                            isPro: true
                        )
                    }
                    .background(Color(hex: "#111827"))
                    .cornerRadius(12)
                    .padding(.horizontal, 24)

                    // Plan selection
                    VStack(spacing: 12) {
                        planButton(
                            id: "annual",
                            title: L10n.isJapaneseLang ? "年額プラン" : "Annual Plan",
                            price: L10n.paywallAnnual,
                            badge: L10n.isJapaneseLang ? "おすすめ" : "Best Value"
                        )
                        .accessibilityIdentifier("paywall_plan_yearly")

                        planButton(
                            id: "monthly",
                            title: L10n.isJapaneseLang ? "月額プラン" : "Monthly Plan",
                            price: L10n.paywallMonthly,
                            badge: nil
                        )
                        .accessibilityIdentifier("paywall_plan_monthly")
                    }
                    .padding(.horizontal, 24)

                    // CTA
                    Button {
                        startTrial()
                    } label: {
                        if isLoading {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        } else {
                            Text(L10n.paywallCTA)
                                .font(.system(size: 18, weight: .semibold))
                                .foregroundColor(.white)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                    .background(Color(hex: "#2dd4bf"))
                    .cornerRadius(14)
                    .padding(.horizontal, 24)
                    .accessibilityIdentifier("paywall_cta")

                    HStack(spacing: 24) {
                        Button {
                            dismiss()
                        } label: {
                            Text(L10n.paywallSkip)
                                .font(.system(size: 14))
                                .foregroundColor(Color(hex: "#6b7280"))
                        }
                        .accessibilityIdentifier("paywall_skip")

                        Button {
                            subscriptionManager.restore()
                        } label: {
                            Text(L10n.paywallRestore)
                                .font(.system(size: 14))
                                .foregroundColor(Color(hex: "#6b7280"))
                        }
                        .accessibilityIdentifier("paywall_restore")
                    }

                    Spacer().frame(height: 32)
                }
            }
        }
        .navigationBarHidden(isOnboarding)
        .onAppear {
            subscriptionManager.fetchOfferings()
            AnalyticsManager.shared.trackPaywallViewed(offeringId: "default")
        }
    }

    private func featureRow(title: String, desc: String, isPro: Bool) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundColor(isPro ? Color(hex: "#2dd4bf") : Color(hex: "#9ca3af"))
                Text(desc)
                    .font(.system(size: 13))
                    .foregroundColor(Color(hex: "#6b7280"))
            }
            Spacer()
        }
        .padding(16)
    }

    private func planButton(id: String, title: String, price: String, badge: String?) -> some View {
        Button {
            selectedPlan = id
        } label: {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text(title)
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundColor(.white)
                        if let badge = badge {
                            Text(badge)
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(.white)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 3)
                                .background(Color(hex: "#2dd4bf"))
                                .cornerRadius(6)
                        }
                    }
                    Text(price)
                        .font(.system(size: 14))
                        .foregroundColor(Color(hex: "#9ca3af"))
                }
                Spacer()
                Circle()
                    .stroke(selectedPlan == id ? Color(hex: "#2dd4bf") : Color(hex: "#374151"), lineWidth: 2)
                    .frame(width: 22, height: 22)
                    .overlay(
                        Circle()
                            .fill(selectedPlan == id ? Color(hex: "#2dd4bf") : Color.clear)
                            .frame(width: 12, height: 12)
                    )
            }
            .padding(16)
            .background(
                selectedPlan == id ?
                Color(hex: "#1e4d6b").opacity(0.5) : Color(hex: "#111827")
            )
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(selectedPlan == id ? Color(hex: "#2dd4bf") : Color(hex: "#1f2937"), lineWidth: 1)
            )
            .cornerRadius(12)
        }
    }

    private func startTrial() {
        guard let offerings = subscriptionManager.offerings,
              let current = offerings.current else { return }

        let pkg: Package?
        if selectedPlan == "annual" {
            pkg = current.annual ?? current.monthly
        } else {
            pkg = current.monthly
        }

        guard let pkg = pkg else { return }
        isLoading = true
        subscriptionManager.purchase(package: pkg)

        DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
            isLoading = false
            if subscriptionManager.isPro { dismiss() }
        }
    }

    private func dismiss() {
        if isOnboarding {
            onboardingCompleted = true
        } else {
            presentationMode.wrappedValue.dismiss()
        }
    }
}
