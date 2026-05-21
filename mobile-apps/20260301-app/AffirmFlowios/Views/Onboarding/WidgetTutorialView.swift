import SwiftUI

struct WidgetTutorialView: View {
    @Environment(UserSettings.self) private var settings

    var body: some View {
        VStack(spacing: Spacing.lg) {
            Text("Add Your Widget")
                .font(.title)
                .fontWeight(.bold)
                .padding(.top, Spacing.xxl)

            // Widget preview
            VStack(spacing: Spacing.md) {
                Text("\"You have the power to create positive change\"")
                    .font(.title3)
                    .multilineTextAlignment(.center)
                    .padding()

                HStack {
                    Image(systemName: "leaf.fill")
                        .foregroundColor(.teal)
                    Text("Calm")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .padding(Spacing.lg)
            .background(Color(.systemBackground))
            .cornerRadius(CornerRadius.large)
            .shadow(color: .black.opacity(0.1), radius: 10)
            .padding(.horizontal, Spacing.xxl)

            VStack(alignment: .leading, spacing: Spacing.md) {
                InstructionRow(number: 1, text: "Long press your home screen")
                InstructionRow(number: 2, text: "Tap the + button")
                InstructionRow(number: 3, text: "Search \"AffirmFlow\"")
                InstructionRow(number: 4, text: "Add the widget")
            }
            .padding(.horizontal, Spacing.xl)

            Spacer()

            VStack(spacing: Spacing.md) {
                Button(action: completeOnboarding) {
                    Text("Done, Let's Go!")
                        .font(.headline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.purple)
                        .cornerRadius(CornerRadius.medium)
                }

                Button(action: completeOnboarding) {
                    Text("Skip for now")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
            }
            .padding(.horizontal, Spacing.xl)
            .padding(.bottom, Spacing.xxl)
        }
    }

    private func completeOnboarding() {
        settings.onboardingComplete = true
    }
}

struct InstructionRow: View {
    let number: Int
    let text: String

    var body: some View {
        HStack(spacing: Spacing.md) {
            Text("\(number)")
                .font(.headline)
                .foregroundColor(.white)
                .frame(width: 28, height: 28)
                .background(Color.purple)
                .clipShape(Circle())

            Text(text)
                .font(.body)

            Spacer()
        }
    }
}

#Preview {
    WidgetTutorialView()
        .environment(UserSettings())
}
