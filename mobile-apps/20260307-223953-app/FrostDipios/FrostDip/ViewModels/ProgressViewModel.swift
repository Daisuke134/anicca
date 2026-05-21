import Foundation

@Observable
final class ProgressViewModel {
    var totalSessions = 0
    var averageDuration: TimeInterval = 0
    var averageTemperature: Double?
    var currentStreak: Int
    var longestStreak: Int

    private let preferences: UserPreferences
    private static let weekdayFormatter: DateFormatter = {
        let f = DateFormatter()
        f.locale = Locale.current
        return f
    }()

    var weekdayLabels: [String] {
        Self.weekdayFormatter.shortWeekdaySymbols ?? ["S", "M", "T", "W", "T", "F", "S"]
    }

    init(defaults: UserDefaults = .standard) {
        self.preferences = UserPreferences(defaults: defaults)
        self.currentStreak = preferences.currentStreak
        self.longestStreak = preferences.longestStreak
    }

    func updateSessions(_ sessions: [PlungeSession]) {
        totalSessions = sessions.count

        if sessions.isEmpty {
            averageDuration = 0
            averageTemperature = nil
            return
        }

        averageDuration = sessions.map(\.duration).reduce(0, +) / Double(sessions.count)

        let temps = sessions.compactMap(\.waterTemperature)
        averageTemperature = temps.isEmpty ? nil : temps.reduce(0, +) / Double(temps.count)
    }

    func refreshStreaks() {
        currentStreak = preferences.currentStreak
        longestStreak = preferences.longestStreak
    }

    func formattedDuration(_ duration: TimeInterval) -> String {
        let minutes = Int(duration) / 60
        let seconds = Int(duration) % 60
        return "\(minutes):\(String(format: "%02d", seconds))"
    }
}
