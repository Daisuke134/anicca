import SwiftUI

struct OnboardingScreen2: View {
    let onNext: () -> Void

    var body: some View {
        VStack(spacing: Spacing.xl) {
            Spacer()

            Image(systemName: "heart.text.square.fill")
                .font(.system(size: 80))
                .foregroundStyle(Color.chiAccent)

            VStack(spacing: Spacing.md) {
                Text(NSLocalizedString("5 Questions, Daily Wisdom", comment: ""))
                    .font(.largeTitle).bold()
                    .multilineTextAlignment(.center)

                Text(NSLocalizedString("Answer 5 simple questions about how you feel today. Chi Daily's AI identifies your TCM constitution and gives you personalized food, movement, and rest guidance.", comment: ""))
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, Spacing.lg)
            }

            VStack(alignment: .leading, spacing: Spacing.sm) {
                FeatureRow(icon: "bolt.fill", text: NSLocalizedString("Energy & sleep patterns", comment: ""))
                FeatureRow(icon: "fork.knife", text: NSLocalizedString("Digestion & nutrition", comment: ""))
                FeatureRow(icon: "heart.fill", text: NSLocalizedString("Emotional balance", comment: ""))
            }
            .padding(.horizontal, Spacing.xl)

            Spacer()

            PrimaryButton(title: NSLocalizedString("Next →", comment: "")) {
                onNext()
            }
            .padding(.horizontal, Spacing.lg)
            .padding(.bottom, Spacing.xl)
        }
    }
}
