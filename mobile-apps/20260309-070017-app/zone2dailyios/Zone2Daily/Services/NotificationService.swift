// File: Services/NotificationService.swift
// Daily Zone 2 reminder notification
// Source: Apple UNUserNotificationCenter — https://developer.apple.com/documentation/usernotifications/unusernotificationcenter
// "Use UNCalendarNotificationTrigger for daily recurring notifications."

import UserNotifications
import Foundation

actor NotificationService {
    static let shared = NotificationService()

    func requestPermission() async -> Bool {
        let center = UNUserNotificationCenter.current()
        let status = try? await center.requestAuthorization(options: [.alert, .sound, .badge])
        return status ?? false
    }

    func scheduleDailyReminder(hour: Int = 8, minute: Int = 0) async {
        let content = UNMutableNotificationContent()
        content.title = NSLocalizedString("notification.title", value: "Zone 2 Time!", comment: "Daily reminder title")
        content.body = NSLocalizedString("notification.body", value: "Ready for your Zone 2 session today?", comment: "Daily reminder body")
        content.sound = .default

        var components = DateComponents()
        components.hour = hour
        components.minute = minute
        let trigger = UNCalendarNotificationTrigger(dateMatching: components, repeats: true)
        let request = UNNotificationRequest(
            identifier: "zone2daily.morning",
            content: content,
            trigger: trigger
        )
        try? await UNUserNotificationCenter.current().add(request)
    }

    func cancelDailyReminder() {
        UNUserNotificationCenter.current().removePendingNotificationRequests(
            withIdentifiers: ["zone2daily.morning"]
        )
    }
}
