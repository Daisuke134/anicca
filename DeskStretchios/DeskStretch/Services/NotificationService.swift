import Foundation
import UserNotifications

final class NotificationService {
    private let center = UNUserNotificationCenter.current()

    func requestPermission() async -> Bool {
        do {
            return try await center.requestAuthorization(options: [.alert, .sound, .badge])
        } catch {
            return false
        }
    }

    func scheduleBreakReminder(intervalMinutes: Int) {
        center.removeAllPendingNotificationRequests()

        let content = UNMutableNotificationContent()
        content.title = String(localized: "Time to stretch!")
        content.body = String(localized: "Take a quick break and stretch your muscles.")
        content.sound = .default

        let trigger = UNTimeIntervalNotificationTrigger(
            timeInterval: TimeInterval(intervalMinutes * 60),
            repeats: true
        )

        let request = UNNotificationRequest(
            identifier: "breakReminder",
            content: content,
            trigger: trigger
        )

        center.add(request)
    }

    func cancelAll() {
        center.removeAllPendingNotificationRequests()
    }
}
