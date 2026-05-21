import SwiftUI

struct NotificationPermissionView: View {
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @State private var navigateToPaywall = false

    var body: some View {
        ZStack {
            Color(hex: "#0a1628").ignoresSafeArea()

            VStack(spacing: 32) {
                Spacer()

                Text("🔔")
                    .font(.system(size: 60))

                VStack(spacing: 12) {
                    Text(L10n.notificationTitle)
                        .font(.system(size: 24, weight: .bold))
                        .foregroundColor(.white)
                        .multilineTextAlignment(.center)

                    Text(L10n.notificationSubtitle)
                        .font(.system(size: 16))
                        .foregroundColor(Color(hex: "#9ca3af"))
                        .multilineTextAlignment(.center)
                }
                .padding(.horizontal, 24)

                VStack(spacing: 8) {
                    featureRow(emoji: "⏰", text: L10n.isJapaneseLang ?
                               "ストレスが高まりやすい時間帯に通知" :
                               "Notified during high-stress hours")
                    featureRow(emoji: "🧠", text: L10n.isJapaneseLang ?
                               "AIがあなたのパターンを学習" :
                               "AI learns your stress patterns")
                    featureRow(emoji: "🎯", text: L10n.isJapaneseLang ?
                               "反応する前にリセット" :
                               "Reset before you react")
                }
                .padding(.horizontal, 24)

                Spacer()

                VStack(spacing: 12) {
                    Button {
                        NotificationManager.shared.requestPermission { _ in
                            navigateToPaywall = true
                        }
                    } label: {
                        Text(L10n.notificationAllow)
                            .font(.system(size: 18, weight: .semibold))
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 16)
                            .background(Color(hex: "#2dd4bf"))
                            .cornerRadius(14)
                    }
                    .accessibilityIdentifier("onboarding-notifications-allow")

                    Button {
                        navigateToPaywall = true
                    } label: {
                        Text(L10n.notificationSkip)
                            .font(.system(size: 16))
                            .foregroundColor(Color(hex: "#6b7280"))
                    }
                }
                .padding(.horizontal, 24)

                NavigationLink(
                    destination: PaywallView(isOnboarding: true).environmentObject(subscriptionManager),
                    isActive: $navigateToPaywall
                ) {
                    EmptyView()
                }

                Spacer().frame(height: 32)
            }
        }
        .navigationBarHidden(true)
    }

    private func featureRow(emoji: String, text: String) -> some View {
        HStack(spacing: 12) {
            Text(emoji)
                .font(.system(size: 20))
            Text(text)
                .font(.system(size: 15))
                .foregroundColor(Color(hex: "#d1d5db"))
            Spacer()
        }
    }
}
