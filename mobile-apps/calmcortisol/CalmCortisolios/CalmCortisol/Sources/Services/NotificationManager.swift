import UserNotifications
import Foundation

class NotificationDelegate: NSObject, UNUserNotificationCenterDelegate {
    static let shared = NotificationDelegate()

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        completionHandler([.banner, .sound])
    }
}

class NotificationManager {
    static let shared = NotificationManager()

    private init() {}

    func requestPermission(completion: @escaping (Bool) -> Void) {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { granted, _ in
            DispatchQueue.main.async {
                completion(granted)
                if granted {
                    self.scheduleDefaultReminders()
                }
            }
        }
    }

    func scheduleDefaultReminders() {
        let times = [(10, 0), (14, 30), (20, 0)]
        for (hour, minute) in times {
            scheduleBreathingReminder(hour: hour, minute: minute)
        }
    }

    private func scheduleBreathingReminder(hour: Int, minute: Int) {
        let content = UNMutableNotificationContent()
        content.title = "CalmCortisol"
        content.body = L10n.isJapaneseLang ? "呼吸で今のストレスをリセットしましょう 🌊" : "Reset your stress with a breathing session 🌊"
        content.sound = .default

        var components = DateComponents()
        components.hour = hour
        components.minute = minute

        let trigger = UNCalendarNotificationTrigger(dateMatching: components, repeats: true)
        let request = UNNotificationRequest(
            identifier: "breathing_reminder_\(hour)_\(minute)",
            content: content,
            trigger: trigger
        )
        UNUserNotificationCenter.current().add(request)
    }
}

extension L10n {
    static var isJapaneseLang: Bool {
        let lang = Locale.current.languageCode ?? "en"
        return lang.hasPrefix("ja")
    }
}
