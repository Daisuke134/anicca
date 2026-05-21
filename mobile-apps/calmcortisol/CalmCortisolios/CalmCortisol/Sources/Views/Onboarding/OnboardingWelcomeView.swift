import SwiftUI

struct OnboardingWelcomeView: View {
    @EnvironmentObject var subscriptionManager: SubscriptionManager

    var body: some View {
        NavigationView {
            ZStack {
                Color(hex: "#0a1628").ignoresSafeArea()

                VStack(spacing: 32) {
                    Spacer()

                    ZStack {
                        Circle()
                            .fill(Color(hex: "#1e4d6b").opacity(0.5))
                            .frame(width: 160, height: 160)

                        Circle()
                            .fill(Color(hex: "#2dd4bf").opacity(0.8))
                            .frame(width: 80, height: 80)

                        Text("🫁")
                            .font(.system(size: 40))
                    }

                    VStack(spacing: 12) {
                        Text(L10n.onboardingWelcomeTitle)
                            .font(.system(size: 36, weight: .bold))
                            .foregroundColor(.white)

                        Text(L10n.onboardingWelcomeSubtitle)
                            .font(.system(size: 18))
                            .foregroundColor(Color(hex: "#9ca3af"))
                            .multilineTextAlignment(.center)
                    }

                    Text(L10n.isJapaneseLang ?
                         "AIがコルチゾールが上がる瞬間を検知し、\n消耗する前に先手で介入します。" :
                         "AI detects when cortisol spikes\nand steps in before you spiral.")
                        .font(.system(size: 15))
                        .foregroundColor(Color(hex: "#6b7280"))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 32)

                    Spacer()

                    NavigationLink(destination: PainSelectionView().environmentObject(subscriptionManager)) {
                        Text(L10n.onboardingWelcomeCTA)
                            .font(.system(size: 18, weight: .semibold))
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 16)
                            .background(Color(hex: "#2dd4bf"))
                            .cornerRadius(14)
                    }
                    .padding(.horizontal, 24)
                    .accessibilityIdentifier("onboarding-welcome-cta")

                    Spacer().frame(height: 32)
                }
            }
            .navigationBarHidden(true)
        }
    }
}
