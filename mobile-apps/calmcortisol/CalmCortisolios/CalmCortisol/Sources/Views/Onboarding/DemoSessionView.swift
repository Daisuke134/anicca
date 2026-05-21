import SwiftUI

struct DemoSessionView: View {
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @State private var animationScale: CGFloat = 1.0
    @State private var showFeedback = false
    @State private var timer: Timer?
    @State private var elapsed = 0

    var body: some View {
        ZStack {
            Color(hex: "#0a1628").ignoresSafeArea()

            if showFeedback {
                feedbackView
            } else {
                sessionView
            }
        }
        .navigationBarHidden(true)
        .onAppear { startBreathingAnimation() }
        .onDisappear { timer?.invalidate() }
    }

    private var sessionView: some View {
        VStack(spacing: 40) {
            Spacer()

            Text(L10n.demoSessionTitle)
                .font(.system(size: 24, weight: .semibold))
                .foregroundColor(.white)

            ZStack {
                Circle()
                    .fill(Color(hex: "#1e4d6b").opacity(0.3))
                    .frame(width: 200, height: 200)
                    .scaleEffect(animationScale)
                    .animation(.easeInOut(duration: 4).repeatForever(autoreverses: true), value: animationScale)

                Circle()
                    .fill(Color(hex: "#2dd4bf").opacity(0.6))
                    .frame(width: 120, height: 120)
                    .scaleEffect(animationScale)

                Text(elapsed < 15 ? L10n.breathingPhaseInhale : L10n.breathingPhaseExhale)
                    .font(.system(size: 16, weight: .medium))
                    .foregroundColor(.white)
            }

            Text(L10n.isJapaneseLang ? "円に合わせて呼吸してください" : "Breathe with the circle")
                .font(.system(size: 15))
                .foregroundColor(Color(hex: "#9ca3af"))

            Spacer()
        }
    }

    private var feedbackView: some View {
        VStack(spacing: 32) {
            Spacer()

            Text("✨")
                .font(.system(size: 60))

            Text(L10n.isJapaneseLang ? "30秒完了！" : "30 seconds done!")
                .font(.system(size: 24, weight: .bold))
                .foregroundColor(.white)

            Text(L10n.isJapaneseLang ? "気持ちよかった？" : "How did that feel?")
                .font(.system(size: 18))
                .foregroundColor(Color(hex: "#9ca3af"))

            VStack(spacing: 12) {
                NavigationLink(destination: NotificationPermissionView().environmentObject(subscriptionManager)) {
                    Text(L10n.demoSessionFeedbackYes)
                        .font(.system(size: 17, weight: .semibold))
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(Color(hex: "#2dd4bf"))
                        .cornerRadius(14)
                }
                .accessibilityIdentifier("demo-feedback-yes")

                NavigationLink(destination: NotificationPermissionView().environmentObject(subscriptionManager)) {
                    Text(L10n.demoSessionFeedbackNo)
                        .font(.system(size: 17))
                        .foregroundColor(Color(hex: "#6b7280"))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(Color(hex: "#1f2937"))
                        .cornerRadius(14)
                }
                .accessibilityIdentifier("demo-feedback-no")
            }
            .padding(.horizontal, 24)

            Spacer()
        }
    }

    private func startBreathingAnimation() {
        animationScale = 1.3
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { _ in
            elapsed += 1
            if elapsed >= 30 {
                timer?.invalidate()
                showFeedback = true
            }
        }
    }
}
