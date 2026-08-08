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
            Text("paywall.title")
                .font(.title2.weight(.semibold))
            Text("paywall.subtitle")
                .multilineTextAlignment(.center)

            Button("paywall.upgrade") {
                Task { await viewModel.upgrade() }
            }
            .buttonStyle(.borderedProminent)
            .accessibilityIdentifier("paywall.upgrade")

            Button("paywall.restore") {
                Task { await viewModel.restorePurchases() }
            }
            .accessibilityIdentifier("paywall.restore")

            if let failure = viewModel.failure {
                Text(LocalizedStringKey(failure.localizedMessageKey))
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("paywall.failure")
            }

            Button("paywall.continueFree", action: onContinueFree)
                .accessibilityIdentifier("paywall.continueFree")
            Button("paywall.notNow", action: onContinueFree)
                .accessibilityIdentifier("paywall.cancel")
        }
        .padding()
    }
}
