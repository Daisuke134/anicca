// File: Views/Onboarding/PaywallView.swift
// F-008: Soft paywall — self-built SwiftUI (Rule 20: RevenueCatUI forbidden)
// Rule 20: [Maybe Later] button mandatory
// Source: RevenueCat — https://docs.revenuecat.com/docs/ios#make-a-purchase
// "Purchases.shared.purchase(package:) is the recommended API."
// Source: Adapty — https://adapty.io/blog/how-to-design-ios-paywall/
// "Animated vs static paywall: 2.9× higher conversion"

import SwiftUI
import RevenueCat

struct PaywallView: View {
    @Environment(\.dismiss) private var dismiss
    @AppStorage("hasCompletedOnboarding") private var hasCompletedOnboarding = false
    @State private var packages: [Package] = []
    @State private var selectedPackage: Package?
    @State private var isPurchasing = false
    @State private var errorMessage: String?
    @State private var isRestoring = false
    @State private var isLoadingOfferings = true
    @State private var restoreMessage: String?

    let subscriptionService: SubscriptionServiceProtocol
    /// Called when the user completes or skips the paywall (onboarding context only)
    var onComplete: (() -> Void)?

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                headerSection
                benefitsSection
                socialProofSection

                if isLoadingOfferings {
                    ProgressView("Loading plans...")
                        .padding()
                } else if packages.isEmpty {
                    Text("Unable to load plans. Check your connection.")
                        .foregroundStyle(.brandDanger)
                        .font(.callout)
                        .multilineTextAlignment(.center)
                } else {
                    pricingSection
                }

                if let error = errorMessage {
                    Text(error)
                        .foregroundStyle(.brandDanger)
                        .font(.callout)
                }

                ctaSection
                faqSection
                legalSection
            }
            .padding()
        }
        .task { await loadPackages() }
        .alert("Restore Purchases", isPresented: Binding(
            get: { restoreMessage != nil },
            set: { if !$0 { restoreMessage = nil } }
        )) {
            Button("OK") { restoreMessage = nil }
        } message: {
            Text(restoreMessage ?? "")
        }
        .accessibilityIdentifier("screen_paywall")
    }

    // MARK: — Sections

    private var headerSection: some View {
        VStack(spacing: 12) {
            Image(systemName: "heart.fill")
                .font(.system(size: 56))
                .foregroundStyle(.brandPrimary)

            Text("Unlock Your Zone 2 Potential")
                .font(.title.bold())
                .multilineTextAlignment(.center)
                .accessibilityIdentifier("paywall_headline")

            Text("Train smarter with Zone 2")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
    }

    private var benefitsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            ForEach([
                ("Unlimited workout history", "checkmark.circle.fill"),
                ("Weekly analytics dashboard", "chart.bar.fill"),
                ("Progress toward 150 min/week goal", "target"),
                ("Daily streak tracking", "flame.fill"),
                ("Personalized Zone 2 HR targets", "heart.circle.fill"),
            ], id: \.0) { benefit, icon in
                Label(benefit, systemImage: icon)
                    .font(.body)
                    .foregroundStyle(.textPrimary)
            }
        }
        .padding()
        .background(.surfaceCard)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var socialProofSection: some View {
        HStack {
            Image(systemName: "heart.fill").foregroundStyle(.brandPrimary)
            Text("Zone 2 is the #1 protocol for metabolic health")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }

    private var pricingSection: some View {
        VStack(spacing: 12) {
            ForEach(packages, id: \.identifier) { pkg in
                PricingCardView(
                    package: pkg,
                    isSelected: selectedPackage?.identifier == pkg.identifier,
                    isBestValue: pkg.packageType == .annual
                ) {
                    selectedPackage = pkg
                }
            }
        }
    }

    private var ctaSection: some View {
        VStack(spacing: 12) {
            Button {
                Task { await purchaseSelected() }
            } label: {
                Group {
                    if isPurchasing {
                        ProgressView().tint(.white)
                    } else {
                        Text("Start Training")
                    }
                }
                .frame(maxWidth: .infinity)
                .padding()
            }
            .buttonStyle(.borderedProminent)
            .tint(.brandPrimary)
            .disabled(selectedPackage == nil || isPurchasing)
            .animation(.easeInOut(duration: 0.2), value: isPurchasing)
            .accessibilityIdentifier("btn_subscribe")

            // Rule 20: [Maybe Later] mandatory
            Button("Maybe Later") {
                hasCompletedOnboarding = true
                onComplete?()
            }
            .foregroundStyle(.secondary)
            .accessibilityIdentifier("btn_maybe_later")

            Button("Restore Purchases") {
                Task { await restorePurchasesAction() }
            }
            .font(.caption)
            .foregroundStyle(.secondary)
            .disabled(isRestoring)
            .accessibilityIdentifier("btn_restore")
        }
    }

    private var faqSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("FAQ")
                .font(.headline)

            FAQRow(q: "When will I be charged?", a: "You will be charged when you subscribe. Cancel anytime in iOS Settings → Apple ID → Subscriptions.")
            FAQRow(q: "How do I cancel?", a: "Go to iOS Settings → Apple ID → Subscriptions → Zone2Daily.")
            FAQRow(q: "Does it work offline?", a: "Yes. All workout data is stored locally on your device.")
        }
        .padding()
        .background(.bgSecondary)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var legalSection: some View {
        HStack {
            if let privacyURL = URL(string: "https://aniccaai.com/privacy") {
                Link("Privacy Policy", destination: privacyURL)
            }
            Text("·")
            if let termsURL = URL(string: "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/") {
                Link("Terms of Use", destination: termsURL)
            }
        }
        .font(.caption)
        .foregroundStyle(.secondary)
    }

    // MARK: — Actions

    private func loadPackages() async {
        isLoadingOfferings = true
        defer { isLoadingOfferings = false }
        #if DEBUG
        // Retry up to 5 times with 2s delay — RC SDK may need time after clearKeychain in E2E tests
        for attempt in 1...5 {
            let result = (try? await subscriptionService.fetchOfferings()) ?? []
            if !result.isEmpty {
                packages = result
                break
            }
            if attempt < 5 { try? await Task.sleep(for: .seconds(2)) }
        }
        #else
        packages = (try? await subscriptionService.fetchOfferings()) ?? []
        #endif
        selectedPackage = packages.first(where: { $0.packageType == .annual }) ?? packages.first
    }

    private func purchaseSelected() async {
        guard let pkg = selectedPackage else { return }
        isPurchasing = true
        defer { isPurchasing = false }
        do {
            _ = try await subscriptionService.purchase(package: pkg)
            hasCompletedOnboarding = true
            onComplete?()
        } catch {
            errorMessage = "Purchase failed. Please try again."
        }
    }

    private func restorePurchasesAction() async {
        isRestoring = true
        defer { isRestoring = false }
        do {
            try await subscriptionService.restorePurchases()
            if subscriptionService.isPremium {
                restoreMessage = "Purchases restored successfully!"
                hasCompletedOnboarding = true
                onComplete?()
            } else {
                restoreMessage = "No active subscription found."
            }
        } catch {
            restoreMessage = "Restore failed. Please try again."
        }
    }
}

// MARK: — Supporting Views

struct PricingCardView: View {
    let package: Package
    let isSelected: Bool
    let isBestValue: Bool
    let onTap: () -> Void

    // UX_SPEC §7: selector_plan_monthly / selector_plan_annual
    private var accessibilityID: String {
        switch package.packageType {
        case .monthly: return "selector_plan_monthly"
        case .annual: return "selector_plan_annual"
        case .weekly: return "selector_plan_weekly"
        default: return "selector_plan_\(package.identifier)"
        }
    }

    var body: some View {
        Button(action: onTap) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text(package.storeProduct.localizedTitle)
                            .font(.headline)
                        if isBestValue {
                            Text("Best Value")
                                .font(.caption.bold())
                                .padding(.horizontal, 8)
                                .padding(.vertical, 2)
                                .background(.brandPrimary)
                                .foregroundStyle(.white)
                                .clipShape(Capsule())
                        }
                    }
                    Text(package.storeProduct.localizedDescription)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Text(package.localizedPriceString)
                    .font(.headline)
            }
            .padding()
            .background(isSelected ? Color.brandPrimary.opacity(0.1) : Color.surfaceCard)
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(isSelected ? Color.brandPrimary : Color.clear, lineWidth: 2)
            )
            .clipShape(RoundedRectangle(cornerRadius: 12))
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier(accessibilityID)
    }
}

struct FAQRow: View {
    let q: String
    let a: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(q).font(.subheadline.bold())
            Text(a).font(.subheadline).foregroundStyle(.secondary)
        }
    }
}
