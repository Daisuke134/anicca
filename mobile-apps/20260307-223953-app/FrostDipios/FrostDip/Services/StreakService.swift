import Foundation

struct StreakService {
    private let preferences: UserPreferences
    private let calendar: Calendar

    init(preferences: UserPreferences = UserPreferences(), calendar: Calendar = .current) {
        self.preferences = preferences
        self.calendar = calendar
    }

    func recordSession() {
        let today = calendar.startOfDay(for: Date())

        if let lastDate = preferences.lastPlungeDate {
            let lastDay = calendar.startOfDay(for: lastDate)

            if calendar.isDate(lastDay, inSameDayAs: today) {
                return
            }

            guard let yesterday = calendar.date(byAdding: .day, value: -1, to: today) else { return }
            if calendar.isDate(lastDay, inSameDayAs: yesterday) {
                preferences.currentStreak = preferences.currentStreak + 1
            } else {
                if !preferences.streakFreezeUsedThisWeek {
                    let daysBetween = calendar.dateComponents([.day], from: lastDay, to: today).day ?? 0
                    if daysBetween == 2 {
                        preferences.streakFreezeUsedThisWeek = true
                        preferences.currentStreak = preferences.currentStreak + 1
                    } else {
                        preferences.currentStreak = 1
                    }
                } else {
                    preferences.currentStreak = 1
                }
            }
        } else {
            preferences.currentStreak = 1
        }

        preferences.lastPlungeDate = Date()

        if preferences.currentStreak > preferences.longestStreak {
            preferences.longestStreak = preferences.currentStreak
        }
    }

    func resetWeeklyFreezeIfNeeded() {
        guard let lastDate = preferences.lastPlungeDate else { return }
        let lastWeekday = calendar.component(.weekday, from: lastDate)
        let currentWeekday = calendar.component(.weekday, from: Date())
        if currentWeekday == 2 && lastWeekday != 2 {
            preferences.streakFreezeUsedThisWeek = false
        }
    }
}
