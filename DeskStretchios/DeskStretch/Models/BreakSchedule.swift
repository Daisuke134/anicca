import Foundation

struct BreakSchedule: Codable {
    var intervalMinutes: Int
    var workHoursStart: Int  // hour (0-23)
    var workHoursEnd: Int    // hour (0-23)
    var isEnabled: Bool

    static let `default` = BreakSchedule(
        intervalMinutes: 45,
        workHoursStart: 9,
        workHoursEnd: 18,
        isEnabled: true
    )
}
