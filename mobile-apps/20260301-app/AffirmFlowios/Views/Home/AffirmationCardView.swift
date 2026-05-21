import SwiftUI

struct AffirmationCardView: View {
    let affirmation: Affirmation?
    let isLoading: Bool
    let errorMessage: String?

    var body: some View {
        VStack(spacing: Spacing.md) {
            if isLoading {
                ProgressView()
                    .scaleEffect(1.5)
                    .frame(height: 100)
            } else if let error = errorMessage {
                VStack(spacing: Spacing.sm) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.title)
                        .foregroundColor(.orange)
                    Text(error)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                }
                .frame(height: 100)
            } else if let affirmation = affirmation {
                Text(affirmation.content)
                    .font(.title)
                    .fontWeight(.semibold)
                    .multilineTextAlignment(.center)
                    .lineSpacing(4)

                HStack {
                    Image(systemName: affirmation.focusArea.systemImage)
                        .foregroundColor(affirmation.focusArea.color)
                    Text(affirmation.focusArea.rawValue)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
        .padding(Spacing.xl)
        .frame(maxWidth: .infinity)
        .background(Color(.secondarySystemBackground))
        .cornerRadius(CornerRadius.large)
        .animation(.bouncy, value: affirmation?.id)
    }
}

#Preview {
    AffirmationCardView(
        affirmation: nil,
        isLoading: true,
        errorMessage: nil
    )
}
