import SwiftUI

struct StretchSessionView: View {
    @Environment(AppState.self) private var appState
    @Environment(\.dismiss) private var dismiss
    let session: StretchSession

    @State private var currentIndex = 0
    @State private var secondsRemaining = 0
    @State private var timer: Timer?
    @State private var isComplete = false

    private let progressService = ProgressService()

    var currentExercise: StretchExercise? {
        guard currentIndex < session.exercises.count else { return nil }
        return session.exercises[currentIndex]
    }

    var exerciseProgress: Double {
        guard let exercise = currentExercise else { return 1.0 }
        let total = Double(exercise.durationSeconds)
        return total > 0 ? Double(total - Double(secondsRemaining)) / total : 0
    }

    var body: some View {
        VStack(spacing: 24) {
            HStack {
                Button(String(localized: "Close")) { dismiss() }
                    .foregroundColor(.secondary)
                Spacer()
                Text("\(currentIndex + 1)/\(session.exercises.count)")
                    .font(.headline)
                    .foregroundColor(.secondary)
            }
            .padding(.horizontal)

            if isComplete {
                completionView
            } else if let exercise = currentExercise {
                exerciseView(exercise)
            }
        }
        .padding(.vertical, 32)
        .onAppear { startExercise() }
        .onDisappear { timer?.invalidate() }
    }

    private func exerciseView(_ exercise: StretchExercise) -> some View {
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

            Spacer()

            TimerRing(
                progress: exerciseProgress,
                timeRemaining: "\(secondsRemaining)"
            )
            .frame(width: 160, height: 160)

            Spacer()

            Button(String(localized: "Skip")) {
                nextExercise()
            }
            .font(.headline)
            .foregroundColor(.secondary)
            .accessibilityIdentifier("stretch_skip")
        }
    }

    private var completionView: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 80))
                .foregroundColor(.green)

            Text(String(localized: "Great job!"))
                .font(.largeTitle)
                .fontWeight(.bold)

            Text(String(localized: "You completed \(session.exercises.count) stretches"))
                .font(.body)
                .foregroundColor(.secondary)

            Spacer()

            PrimaryButton(title: String(localized: "Done")) {
                dismiss()
            }
            .padding(.horizontal, 24)
            .accessibilityIdentifier("stretch_done")
        }
    }

    private func startExercise() {
        guard let exercise = currentExercise else {
            completeSession()
            return
        }
        secondsRemaining = exercise.durationSeconds
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { _ in
            if secondsRemaining > 0 {
                secondsRemaining -= 1
                if secondsRemaining <= 3 && secondsRemaining > 0 {
                    let generator = UIImpactFeedbackGenerator(style: .light)
                    generator.impactOccurred()
                }
            } else {
                nextExercise()
            }
        }
    }

    private func nextExercise() {
        timer?.invalidate()
        if currentIndex + 1 < session.exercises.count {
            currentIndex += 1
            startExercise()
        } else {
            completeSession()
        }
    }

    private func completeSession() {
        timer?.invalidate()
        isComplete = true
        let duration = session.totalDurationSeconds / 60
        let updated = progressService.recordSession(duration: max(1, duration), current: appState.userProgress)
        appState.userProgress = updated
        appState.persistProgress()

        let generator = UINotificationFeedbackGenerator()
        generator.notificationOccurred(.success)
    }
}
