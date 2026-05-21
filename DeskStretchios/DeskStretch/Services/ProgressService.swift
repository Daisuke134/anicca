import Foundation

final class ProgressService {
    func recordSession(duration: Int, current: UserProgress) -> UserProgress {
        let today = Calendar.current.startOfDay(for: Date())
        let todayKey = ISO8601DateFormatter().string(from: today)
        let lastActive = current.lastActiveDate.map { Calendar.current.startOfDay(for: $0) }

        let isFirstToday = lastActive != today
        let yesterday = Calendar.current.date(byAdding: .day, value: -1, to: today)
        let isConsecutive = lastActive == yesterday

        var updated = current
        updated.todayCount = isFirstToday ? 1 : current.todayCount + 1
        updated.streak = isFirstToday ? (isConsecutive ? current.streak + 1 : 1) : current.streak
        updated.totalSessions = current.totalSessions + 1
        updated.totalMinutes = current.totalMinutes + duration
        updated.lastActiveDate = Date()

        var weekHistory = current.weekHistory
        weekHistory[todayKey] = (weekHistory[todayKey] ?? 0) + 1
        updated.weekHistory = weekHistory

        return updated
    }
}
