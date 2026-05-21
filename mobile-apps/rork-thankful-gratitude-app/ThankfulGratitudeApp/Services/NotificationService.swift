import Foundation
import UserNotifications

@Observable
@MainActor
class NotificationService {
    var morningTime: Date = {
        var components = DateComponents()
        components.hour = 8
        components.minute = 0
        return Calendar.current.date(from: components) ?? Date()
    }()

    var eveningTime: Date = {
        var components = DateComponents()
        components.hour = 21
        components.minute = 0
        return Calendar.current.date(from: components) ?? Date()
    }()

    var isAuthorized: Bool = false

    func requestPermission() async {
        do {
            let granted = try await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge])
            isAuthorized = granted
        } catch {
            isAuthorized = false
        }
    }

    func scheduleNotifications(language: AppLanguage) {
        UNUserNotificationCenter.current().removeAllPendingNotificationRequests()

        let morningContent = UNMutableNotificationContent()
        let eveningContent = UNMutableNotificationContent()

        switch language {
        case .english:
            morningContent.title = "Thankful"
            morningContent.body = "Good morning! Start your day with gratitude 🌅"
            eveningContent.title = "Thankful"
            eveningContent.body = "How was your day? Write 3 things you're grateful for 🌙"
        case .japanese:
            morningContent.title = "Thankful"
            morningContent.body = "おはよう！感謝で1日を始めよう 🌅"
            eveningContent.title = "Thankful"
            eveningContent.body = "今日はどうだった？感謝を3つ書こう 🌙"
        }

        morningContent.sound = .default
        eveningContent.sound = .default

        let morningComponents = Calendar.current.dateComponents([.hour, .minute], from: morningTime)
        let eveningComponents = Calendar.current.dateComponents([.hour, .minute], from: eveningTime)

        let morningTrigger = UNCalendarNotificationTrigger(dateMatching: morningComponents, repeats: true)
        let eveningTrigger = UNCalendarNotificationTrigger(dateMatching: eveningComponents, repeats: true)

        let morningRequest = UNNotificationRequest(identifier: "morning_reminder", content: morningContent, trigger: morningTrigger)
        let eveningRequest = UNNotificationRequest(identifier: "evening_reminder", content: eveningContent, trigger: eveningTrigger)

        UNUserNotificationCenter.current().add(morningRequest)
        UNUserNotificationCenter.current().add(eveningRequest)
    }
}
