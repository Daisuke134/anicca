import Foundation

struct UserProgress: Codable {
    var todayCount: Int
    var streak: Int
    var totalSessions: Int
    var totalMinutes: Int
    var lastActiveDate: Date?
    var weekHistory: [String: Int]  // ISO date string → session count

    static let empty = UserProgress(
        todayCount: 0,
        streak: 0,
        totalSessions: 0,
        totalMinutes: 0,
        lastActiveDate: nil,
        weekHistory: [:]
    )
}
