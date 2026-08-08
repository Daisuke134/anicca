import SwiftUI

struct SoftPaywallView: View {
    @State private var viewModel: SoftPaywallViewModel
    private let onContinueFree: () -> Void

    init(
        viewModel: SoftPaywallViewModel? = nil,
        purchasing: PaywallPurchasing? = nil,
        onContinueFree: @escaping () -> Void
    ) {
        _viewModel = State(initialValue: viewModel ?? SoftPaywallViewModel(purchasing: purchasing))
        self.onContinueFree = onContinueFree
    }

    var body: some View {
        VStack(spacing: 18) {
            Text("More support when you want it")
                .font(.title2.weight(.semibold))
            Text("Keep using your route and chat for free. Upgrade only when it helps.")
                .multilineTextAlignment(.center)

            Button("Upgrade") {
                Task { await viewModel.upgrade() }
            }
            .buttonStyle(.borderedProminent)
            .accessibilityIdentifier("paywall.upgrade")

            Button("Restore purchases") {
                Task { await viewModel.restorePurchases() }
            }
            .accessibilityIdentifier("paywall.restore")

            if let failure = viewModel.failure {
                Text(failure.localizedMessageKey)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("paywall.failure")
            }

            Button("Continue free", action: onContinueFree)
                .accessibilityIdentifier("paywall.continueFree")
            Button("Not now", action: onContinueFree)
                .accessibilityIdentifier("paywall.cancel")
        }
        .padding()
    }
}
