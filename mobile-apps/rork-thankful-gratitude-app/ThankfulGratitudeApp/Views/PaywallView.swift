import SwiftUI
import RevenueCat

struct PaywallView: View {
    let language: AppLanguage
    let onDismiss: () -> Void
    let onPurchaseSuccess: () -> Void

    @State private var selectedPlan: PlanType = .annual
    @State private var isPurchasing: Bool = false
    @State private var offerings: Offerings?
    @State private var showError: Bool = false
    @State private var errorMessage: String = ""

    private enum PlanType {
        case monthly, annual
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Spacer()
                Button {
                    onDismiss()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title2)
                        .symbolRenderingMode(.hierarchical)
                        .foregroundStyle(.secondary)
                }
                .accessibilityIdentifier("paywall_skip")
            }
            .padding(.horizontal, 20)
            .padding(.top, 12)

            ScrollView(showsIndicators: false) {
                VStack(spacing: 28) {
                    VStack(spacing: 8) {
                        Image(systemName: "heart.circle.fill")
                            .font(.system(size: 56))
                            .foregroundStyle(
                                LinearGradient(
                                    colors: [Color(red: 0.83, green: 0.65, blue: 0.46), Color(red: 0.49, green: 0.71, blue: 0.62)],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )

                        Text(L10n.paywallHeadline(language))
                            .font(.title.bold())
                            .multilineTextAlignment(.center)
                    }
                    .padding(.top, 8)

                    VStack(alignment: .leading, spacing: 16) {
                        featureRow(icon: "infinity", text: L10n.paywallBullet1(language))
                        featureRow(icon: "sparkles", text: L10n.paywallBullet2(language))
                        featureRow(icon: "chart.line.uptrend.xyaxis", text: L10n.paywallBullet3(language))
                    }
                    .padding(.horizontal, 8)

                    VStack(spacing: 12) {
                        planCard(
                            isSelected: selectedPlan == .annual,
                            badge: L10n.bestValue(language),
                            title: language == .english ? "Annual" : "年額",
                            price: L10n.annualPrice(language),
                            detail: L10n.annualTrial(language)
                        ) {
                            selectedPlan = .annual
                        }
                        .accessibilityIdentifier("paywall_plan_yearly")

                        planCard(
                            isSelected: selectedPlan == .monthly,
                            badge: nil,
                            title: language == .english ? "Monthly" : "月額",
                            price: L10n.monthlyPrice(language),
                            detail: nil
                        ) {
                            selectedPlan = .monthly
                        }
                        .accessibilityIdentifier("paywall_plan_monthly")
                    }

                    VStack(spacing: 16) {
                        Button {
                            Task { await purchase() }
                        } label: {
                            HStack(spacing: 8) {
                                if isPurchasing {
                                    ProgressView()
                                        .tint(.white)
                                }
                                Text(selectedPlan == .annual ? L10n.startTrial(language) : (language == .english ? "Subscribe Now" : "今すぐ登録"))
                                    .font(.headline)
                            }
                            .foregroundStyle(.white)
                            .frame(maxWidth: .infinity)
                            .frame(height: 56)
                            .background(
                                LinearGradient(
                                    colors: [Color(red: 0.83, green: 0.65, blue: 0.46), Color(red: 0.76, green: 0.55, blue: 0.36)],
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                            .clipShape(.rect(cornerRadius: 16))
                        }
                        .disabled(isPurchasing)
                        .accessibilityIdentifier("paywall_cta")

                        Text(L10n.finePrint(language))
                            .font(.caption)
                            .foregroundStyle(.tertiary)
                            .multilineTextAlignment(.center)

                        Button {
                            Task { await restore() }
                        } label: {
                            Text(L10n.restorePurchase(language))
                                .font(.subheadline)
                                .foregroundStyle(Color(red: 0.83, green: 0.65, blue: 0.46))
                        }
                        .accessibilityIdentifier("paywall_restore")
                    }
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 40)
                .frame(maxWidth: 700)
                .frame(maxWidth: .infinity)
            }
        }
        .background(
            LinearGradient(
                colors: [Color(red: 1.0, green: 0.98, blue: 0.95), Color(red: 0.99, green: 0.94, blue: 0.88)],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()
        )
        .task {
            await fetchOfferings()
        }
        .alert("Error", isPresented: $showError) {
            Button("OK") { }
        } message: {
            Text(errorMessage)
        }
    }

    private func featureRow(icon: String, text: String) -> some View {
        HStack(spacing: 14) {
            Image(systemName: icon)
                .font(.body.weight(.semibold))
                .foregroundStyle(Color(red: 0.49, green: 0.71, blue: 0.62))
                .frame(width: 28)

            Text(text)
                .font(.body)
        }
    }

    private func planCard(isSelected: Bool, badge: String?, title: String, price: String, detail: String?, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 8) {
                        Text(title)
                            .font(.headline)

                        if let badge {
                            Text(badge)
                                .font(.caption2.bold())
                                .foregroundStyle(.white)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 3)
                                .background(Color(red: 0.49, green: 0.71, blue: 0.62))
                                .clipShape(.rect(cornerRadius: 6))
                        }
                    }

                    if let detail {
                        Text(detail)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                Spacer()

                Text(price)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(isSelected ? Color(red: 0.83, green: 0.65, blue: 0.46) : .secondary)
            }
            .padding(16)
            .background(
                RoundedRectangle(cornerRadius: 14)
                    .fill(Color(.secondarySystemGroupedBackground))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 14)
                    .stroke(isSelected ? Color(red: 0.83, green: 0.65, blue: 0.46) : .clear, lineWidth: 2)
            )
        }
        .buttonStyle(.plain)
        .sensoryFeedback(.selection, trigger: isSelected)
    }

    private func fetchOfferings() async {
        guard Purchases.isConfigured else { return }
        do {
            offerings = try await Purchases.shared.offerings()
        } catch {
            // Silently fail — show static prices
        }
    }

    private func purchase() async {
        guard Purchases.isConfigured else { return }
        isPurchasing = true
        defer { isPurchasing = false }

        do {
            guard let current = offerings?.current else {
                onPurchaseSuccess()
                return
            }

            let packageId = selectedPlan == .annual ? "$rc_annual" : "$rc_monthly"
            guard let package = current.package(identifier: packageId) ?? current.availablePackages.first else {
                onPurchaseSuccess()
                return
            }

            let result = try await Purchases.shared.purchase(package: package)
            if result.customerInfo.entitlements["pro"]?.isActive == true {
                onPurchaseSuccess()
            }
        } catch {
            if !error.localizedDescription.contains("cancelled") {
                errorMessage = error.localizedDescription
                showError = true
            }
        }
    }

    private func restore() async {
        guard Purchases.isConfigured else { return }
        isPurchasing = true
        defer { isPurchasing = false }

        do {
            let info = try await Purchases.shared.restorePurchases()
            if info.entitlements["pro"]?.isActive == true {
                onPurchaseSuccess()
            }
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }
}
