import Foundation

struct StretchSession: Codable, Identifiable {
    let id: String
    let exercises: [StretchExercise]
    let startedAt: Date
    var completedAt: Date?
    var totalDurationSeconds: Int

    init(exercises: [StretchExercise]) {
        self.id = UUID().uuidString
        self.exercises = exercises
        self.startedAt = Date()
        self.completedAt = nil
        self.totalDurationSeconds = exercises.reduce(0) { $0 + $1.durationSeconds }
    }
}
