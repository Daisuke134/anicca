import SwiftUI

struct PaywallView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var offerings: MockOfferings?
    @State private var selectedPackage: MockPackage?
    @State private var isPurchasing = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: Spacing.xl) {
                    // Header
                    VStack(spacing: Spacing.md) {
                        Image(systemName: "sparkles")
                            .font(.system(size: 60))
                            .foregroundStyle(.linearGradient(
                                colors: [.purple, .pink],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ))

                        Text("Unlock Premium")
                            .font(.title)
                            .fontWeight(.bold)

                        Text("Unlimited AI affirmations")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                    .padding(.top, Spacing.xl)

                    // Features
                    VStack(alignment: .leading, spacing: Spacing.md) {
                        FeatureRow(icon: "infinity", title: "Unlimited Refreshes", subtitle: "No daily limits")
                        FeatureRow(icon: "brain.head.profile", title: "Advanced AI", subtitle: "Smarter affirmations")
                        FeatureRow(icon: "star.fill", title: "Exclusive Themes", subtitle: "Beautiful widget styles")
                    }
                    .padding(.horizontal, Spacing.lg)

                    // Packages
                    if let offerings = offerings, let current = offerings.current {
                        VStack(spacing: Spacing.md) {
                            ForEach(current.availablePackages) { package in
                                PackageButton(
                                    package: package,
                                    isSelected: selectedPackage?.identifier == package.identifier
                                ) {
                                    selectedPackage = package
                                }
                            }
                        }
                        .padding(.horizontal, Spacing.lg)
                    } else {
                        ProgressView()
                            .padding()
                    }

                    // Error
                    if let error = errorMessage {
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal)
                    }

                    // Purchase Button
                    Button(action: purchase) {
                        HStack {
                            if isPurchasing {
                                ProgressView()
                                    .tint(.white)
                            } else {
                                Text("Continue")
                            }
                        }
                        .font(.headline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(selectedPackage == nil ? Color.gray : Color.purple)
                        .cornerRadius(CornerRadius.medium)
                    }
                    .disabled(selectedPackage == nil || isPurchasing)
                    .padding(.horizontal, Spacing.lg)

                    // Footer
                    VStack(spacing: Spacing.xs) {
                        Button("Restore Purchases") {
                            Task {
                                try? await SubscriptionService.shared.restorePurchases()
                                dismiss()
                            }
                        }
                        .font(.caption)

                        Text("Cancel anytime. Terms apply.")
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                    }
                    .padding(.bottom, Spacing.xl)
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(action: { dismiss() }) {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(.secondary)
                    }
                }
            }
            .task {
                await SubscriptionService.shared.fetchOfferings()
                offerings = SubscriptionService.shared.offerings
                selectedPackage = offerings?.current?.availablePackages.first
            }
        }
    }

    private func purchase() {
        guard let package = selectedPackage else { return }
        isPurchasing = true
        errorMessage = nil

        Task {
            do {
                try await SubscriptionService.shared.purchase(package: package)
                dismiss()
            } catch {
                errorMessage = error.localizedDescription
            }
            isPurchasing = false
        }
    }
}

struct FeatureRow: View {
    let icon: String
    let title: String
    let subtitle: String

    var body: some View {
        HStack(spacing: Spacing.md) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(.purple)
                .frame(width: 32)

            VStack(alignment: .leading, spacing: Spacing.xxs) {
                Text(title)
                    .font(.headline)
                Text(subtitle)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }

            Spacer()
        }
        .padding(Spacing.md)
        .background(Color.purple.opacity(0.05))
        .cornerRadius(CornerRadius.medium)
    }
}

struct PackageButton: View {
    let package: MockPackage
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                VStack(alignment: .leading, spacing: Spacing.xxs) {
                    Text(package.localizedTitle)
                        .font(.headline)
                        .foregroundColor(.primary)
                    Text(package.localizedDescription)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                Spacer()

                Text(package.localizedPriceString)
                    .font(.headline)
                    .foregroundColor(isSelected ? .white : .primary)
                    .padding(.horizontal, Spacing.md)
                    .padding(.vertical, Spacing.xs)
                    .background(isSelected ? Color.purple : Color.clear)
                    .cornerRadius(CornerRadius.small)
            }
            .padding(Spacing.md)
            .background(isSelected ? Color.purple.opacity(0.1) : Color(.systemBackground))
            .cornerRadius(CornerRadius.medium)
            .overlay(
                RoundedRectangle(cornerRadius: CornerRadius.medium)
                    .stroke(isSelected ? Color.purple : Color.gray.opacity(0.2), lineWidth: isSelected ? 2 : 1)
            )
        }
    }
}

#Preview {
    PaywallView()
}
