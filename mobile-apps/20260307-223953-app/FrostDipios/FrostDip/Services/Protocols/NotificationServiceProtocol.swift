import Foundation

protocol NotificationServiceProtocol {
    func requestPermission() async throws -> Bool
    func scheduleReminder(at time: DateComponents, title: String, body: String)
    func scheduleStreakWarning()
    func cancelAll()
}
