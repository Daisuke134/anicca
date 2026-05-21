import Foundation
import UserNotifications

protocol NotificationServiceProtocol {
    func requestPermission() async -> Bool
    func scheduleBreakNotification(after interval: TimeInterval)
    func cancelAll()
}

final class NotificationService: NotificationServiceProtocol {
    func requestPermission() async -> Bool {
        do {
            return try await UNUserNotificationCenter.current()
                .requestAuthorization(options: [.alert, .sound, .badge])
        } catch {
            return false
        }
    }

    func scheduleBreakNotification(after interval: TimeInterval) {
        let content = UNMutableNotificationContent()
        content.title = String(localized: "timer.break.title")
        content.body = String(localized: "timer.break.instruction")
        content.sound = .default

        let trigger = UNTimeIntervalNotificationTrigger(
            timeInterval: max(interval, 1),
            repeats: false
        )

        let request = UNNotificationRequest(
            identifier: "eyebreak-\(UUID().uuidString)",
            content: content,
            trigger: trigger
        )

        UNUserNotificationCenter.current().add(request)
    }

    func cancelAll() {
        UNUserNotificationCenter.current().removeAllPendingNotificationRequests()
    }
}
