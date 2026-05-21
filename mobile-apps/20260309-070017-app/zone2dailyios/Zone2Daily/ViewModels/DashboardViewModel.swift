// File: ViewModels/DashboardViewModel.swift
// Implements F-004: Weekly Zone 2 progress calculation
// Source: Apple Swift Evolution SE-0395 — @Observable
// "@Observable replaces ObservableObject with zero boilerplate."

import Foundation
import Observation

/// 7-day activity entry for the weekly bar chart
struct WeekdayActivity {
    let label: String       // e.g. "Mon"
    let hasActivity: Bool
    let minutes: Double
}

@Observable
final class DashboardViewModel {
    var weeklyZone2Minutes: Double = 0
    var weeklyGoalMinutes: Int = 150
    var streak: Int = 0
    var weekdayActivity: [WeekdayActivity] = []

    /// Reused across calls — Source: docs/IMPLEMENTATION_GUIDE.md — M-001 DateFormatter optimization
    private static let weekdayFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "EEE"  // "Mon", "Tue", etc.
        return f
    }()

    func loadWeeklyData(sessions: [WorkoutSession]) {
        let calendar = Calendar.current
        // Source: docs/IMPLEMENTATION_GUIDE.md — M-001 fix: dateInterval(of:)
        let startOfWeek = calendar.dateInterval(of: .weekOfYear, for: .now)?.start ?? .now
        let thisWeek = sessions.filter { $0.date >= startOfWeek }
        weeklyZone2Minutes = thisWeek.reduce(0) { $0 + $1.zone2Minutes }
        streak = calculateStreak(sessions: sessions)
        weekdayActivity = buildWeekdayActivity(sessions: sessions, calendar: calendar)
    }

    var progressFraction: Double {
        min(weeklyZone2Minutes / Double(weeklyGoalMinutes), 1.0)
    }

    /// Build 7 entries ending today, ordered oldest → newest
    private func buildWeekdayActivity(sessions: [WorkoutSession], calendar: Calendar) -> [WeekdayActivity] {
        return (0..<7).map { offset in
            let date = calendar.date(byAdding: .day, value: -(6 - offset), to: .now)!
            let dayStart = calendar.startOfDay(for: date)
            let dayEnd = calendar.date(byAdding: .day, value: 1, to: dayStart)!
            let daySessions = sessions.filter { $0.date >= dayStart && $0.date < dayEnd }
            let dayMinutes = daySessions.reduce(0.0) { $0 + $1.zone2Minutes }
            return WeekdayActivity(
                label: Self.weekdayFormatter.string(from: date),
                hasActivity: dayMinutes > 0,
                minutes: dayMinutes
            )
        }
    }

    /// Count consecutive days ending today where zone2Seconds > 0 — O(n)
    private func calculateStreak(sessions: [WorkoutSession]) -> Int {
        let calendar = Calendar.current
        // Build Set of active days for O(1) lookup
        let activeDays = Set(sessions
            .filter { $0.zone2Seconds > 0 }
            .map { calendar.startOfDay(for: $0.date) }
        )
        var count = 0
        var checkDate = calendar.startOfDay(for: .now)
        for _ in 0..<365 {
            guard activeDays.contains(checkDate) else { break }
            count += 1
            guard let prev = calendar.date(byAdding: .day, value: -1, to: checkDate) else { break }
            checkDate = prev
        }
        return count
    }

    func canLogWorkout(sessions: [WorkoutSession], isPremium: Bool) -> Bool {
        guard !isPremium else { return true }
        let sevenDaysAgo = Calendar.current.date(byAdding: .day, value: -7, to: .now) ?? .now
        let recentCount = sessions.filter { $0.date >= sevenDaysAgo }.count
        return recentCount < 3
    }
}
