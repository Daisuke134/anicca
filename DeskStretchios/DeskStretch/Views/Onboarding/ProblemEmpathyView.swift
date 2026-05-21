import SwiftUI

struct ProblemEmpathyView: View {
    let onNext: () -> Void

    var body: some View {
        VStack(spacing: 32) {
            Spacer()

            Image(systemName: "figure.mind.and.body")
                .font(.system(size: 80))
                .foregroundColor(.accentColor)

            VStack(spacing: 12) {
                Text(String(localized: "Sitting all day?"))
                    .font(.largeTitle)
                    .fontWeight(.bold)

                Text(String(localized: "Your body needs regular breaks.\nDeskStretch reminds you to stretch\nand guides you through quick routines."))
                    .font(.body)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .lineSpacing(4)
            }

            Spacer()

            PrimaryButton(title: String(localized: "Get Started")) {
                onNext()
            }
            .accessibilityIdentifier("onboarding_get_started")
        }
        .padding(.horizontal, 24)
        .padding(.bottom, 32)
    }
}
