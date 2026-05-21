import SwiftUI

struct OnboardingScreen1: View {
    let onNext: () -> Void

    var body: some View {
        VStack(spacing: Spacing.xl) {
            Spacer()

            Image(systemName: "leaf.circle.fill")
                .font(.system(size: 80))
                .foregroundStyle(Color.chiAccent)

            VStack(spacing: Spacing.md) {
                Text(NSLocalizedString("Welcome to Chi Daily", comment: ""))
                    .font(.largeTitle).bold()
                    .multilineTextAlignment(.center)

                Text(NSLocalizedString("Your daily TCM wellness companion powered by on-device AI.", comment: ""))
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, Spacing.lg)
            }

            Spacer()

            PrimaryButton(title: NSLocalizedString("Next →", comment: "")) {
                onNext()
            }
            .padding(.horizontal, Spacing.lg)
            .padding(.bottom, Spacing.xl)
        }
    }
}
