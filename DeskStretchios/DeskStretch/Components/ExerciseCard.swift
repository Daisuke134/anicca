import SwiftUI

struct ExerciseCard: View {
    let exercise: StretchExercise
    let isPremium: Bool
    let isLocked: Bool

    var body: some View {
        HStack(spacing: 16) {
            Image(systemName: exercise.sfSymbol)
                .font(.title2)
                .foregroundColor(.accentColor)
                .frame(width: 44, height: 44)
                .background(Color.accentColor.opacity(0.12))
                .cornerRadius(12)

            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(exercise.name)
                        .font(.body)
                        .fontWeight(.medium)

                    if isLocked {
                        Image(systemName: "lock.fill")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                Text("\(exercise.durationSeconds)s")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()

            Image(systemName: "chevron.right")
                .foregroundColor(.secondary)
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .opacity(isLocked ? 0.6 : 1.0)
    }
}
