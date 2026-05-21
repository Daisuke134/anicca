import SwiftUI

struct WelcomeView: View {
    let onContinue: () -> Void

    var body: some View {
        VStack(spacing: Spacing.xxl) {
            Spacer()

            Image(systemName: "sparkles")
                .font(.system(size: 80))
                .foregroundStyle(.linearGradient(
                    colors: [.purple, .pink],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                ))

            VStack(spacing: Spacing.md) {
                Text("AffirmFlow")
                    .font(.largeTitle)
                    .fontWeight(.bold)

                Text("AI-powered affirmations\n100% on your device")
                    .font(.title3)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }

            HStack(spacing: Spacing.sm) {
                Image(systemName: "lock.fill")
                    .foregroundColor(.green)
                Text("Your thoughts never leave your phone")
                    .font(.subheadline)
            }
            .padding()
            .background(Color.green.opacity(0.1))
            .cornerRadius(CornerRadius.medium)

            Spacer()

            Button(action: onContinue) {
                Text("Get Started")
                    .font(.headline)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.purple)
                    .cornerRadius(CornerRadius.medium)
            }
            .padding(.horizontal, Spacing.xl)
        }
        .padding(.bottom, Spacing.xxl)
    }
}

#Preview {
    WelcomeView(onContinue: {})
}
