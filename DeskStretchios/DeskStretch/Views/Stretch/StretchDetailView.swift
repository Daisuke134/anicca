import SwiftUI

struct StretchDetailView: View {
    let exercise: StretchExercise

    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: exercise.sfSymbol)
                .font(.system(size: 60))
                .foregroundColor(.accentColor)

            Text(exercise.name)
                .font(.title)
                .fontWeight(.bold)

            Text(exercise.instructions)
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal)

            HStack(spacing: 8) {
                Image(systemName: "clock")
                Text("\(exercise.durationSeconds)s")
            }
            .font(.headline)
            .foregroundColor(.secondary)

            Spacer()
        }
        .padding(.vertical, 32)
        .navigationTitle(exercise.name)
        .navigationBarTitleDisplayMode(.inline)
    }
}
