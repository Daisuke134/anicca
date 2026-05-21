import SwiftUI

struct PainSelectionView: View {
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @State private var selectedPain: String?

    let pains: [(id: String, label: String, emoji: String)] = [
        ("work", L10n.painOptionWork, "💼"),
        ("sleep", L10n.painOptionSleep, "😴"),
        ("anxiety", L10n.painOptionAnxiety, "😰"),
        ("anger", L10n.painOptionAnger, "😤")
    ]

    var body: some View {
        ZStack {
            Color(hex: "#0a1628").ignoresSafeArea()

            VStack(spacing: 24) {
                Spacer().frame(height: 40)

                Text(L10n.painSelectionTitle)
                    .font(.system(size: 26, weight: .bold))
                    .foregroundColor(.white)
                    .multilineTextAlignment(.center)

                VStack(spacing: 12) {
                    ForEach(pains, id: \.id) { pain in
                        Button {
                            selectedPain = pain.id
                        } label: {
                            HStack(spacing: 16) {
                                Text(pain.emoji)
                                    .font(.system(size: 28))
                                Text(pain.label)
                                    .font(.system(size: 17, weight: .medium))
                                    .foregroundColor(.white)
                                Spacer()
                                if selectedPain == pain.id {
                                    Image(systemName: "checkmark.circle.fill")
                                        .foregroundColor(Color(hex: "#2dd4bf"))
                                }
                            }
                            .padding(16)
                            .background(
                                selectedPain == pain.id ?
                                Color(hex: "#1e4d6b") : Color(hex: "#111827")
                            )
                            .cornerRadius(12)
                        }
                        .accessibilityIdentifier("pain-option-\(pain.id)")
                    }
                }
                .padding(.horizontal, 24)

                Spacer()

                NavigationLink(
                    destination: DemoSessionView().environmentObject(subscriptionManager),
                    isActive: .constant(selectedPain != nil)
                ) {
                    EmptyView()
                }

                if selectedPain != nil {
                    NavigationLink(destination: DemoSessionView()
                        .environmentObject(subscriptionManager)
                        .onAppear {
                            if let pain = selectedPain {
                                AnalyticsManager.shared.trackOnboardingCompleted(painType: pain)
                            }
                        }
                    ) {
                        Text(L10n.isJapaneseLang ? "次へ" : "Next")
                            .font(.system(size: 18, weight: .semibold))
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 16)
                            .background(Color(hex: "#2dd4bf"))
                            .cornerRadius(14)
                    }
                    .padding(.horizontal, 24)
                }

                Spacer().frame(height: 32)
            }
        }
        .navigationBarHidden(true)
    }
}
