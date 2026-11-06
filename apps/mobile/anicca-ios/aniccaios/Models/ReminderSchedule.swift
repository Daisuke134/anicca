import Foundation

/// Display contract of the deployed affirmation sender (4e7885b).
/// Times use the timezone registered by PushTokenService; these are planned sends,
/// not a promise of delivery while notifications are disabled or the device is offline.
enum ReminderSchedule {
    static func slots(isPro: Bool) -> [String] {
        isPro ? ["08:00", "12:30", "17:30", "21:30"] : ["09:00", "14:00", "20:00"]
    }
}
