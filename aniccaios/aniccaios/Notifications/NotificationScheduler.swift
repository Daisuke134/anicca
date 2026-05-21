import Foundation
import UserNotifications
import OSLog

/// 通知スケジューラ（スリム版）
/// - 認証リクエスト
/// - カテゴリ登録
/// - サーバー駆動型Nudge通知
@MainActor
final class NotificationScheduler {
    static let shared = NotificationScheduler()

    enum Category: String {
        case nudge = "NUDGE"
    }

    enum Action: String {
        case startConversation = "START_CONVERSATION"
        case dismissAll = "DISMISS_ALL"
    }

    private let center = UNUserNotificationCenter.current()
    private let logger = Logger(subsystem: "com.anicca.ios", category: "NotificationScheduler")

    private init() {}

    // MARK: - Localization Helper

    private func localizedString(_ key: String, comment: String = "") -> String {
        let language = AppState.shared.userProfile.preferredLanguage
        guard let path = Bundle.main.path(forResource: language.rawValue, ofType: "lproj"),
              let bundle = Bundle(path: path) else {
            return NSLocalizedString(key, comment: comment)
        }
        return NSLocalizedString(key, tableName: nil, bundle: bundle, value: key, comment: comment)
    }

    // MARK: - Authorization

    @discardableResult
    func requestAuthorization() async -> Bool {
        do {
            var options: UNAuthorizationOptions = [.alert, .sound, .badge]
            if #available(iOS 15.0, *) {
                options.insert(.timeSensitive)
            }
            let notificationsGranted = try await center.requestAuthorization(options: options)
            return notificationsGranted
        } catch {
            logger.error("Notification authorization error: \(error.localizedDescription, privacy: .public)")
            return false
        }
    }

    @discardableResult
    func requestAuthorizationIfNeeded() async -> Bool {
        let settings = await center.notificationSettings()
        switch settings.authorizationStatus {
        case .notDetermined:
            return await requestAuthorization()
        case .authorized, .provisional, .ephemeral:
            return true
        default:
            return false
        }
    }

    func isAuthorizedForAlerts() async -> Bool {
        let settings = await center.notificationSettings()
        switch settings.authorizationStatus {
        case .authorized, .provisional, .ephemeral:
            return true
        default:
            return false
        }
    }

    // MARK: - Categories

    func registerCategories() {
        let start = UNNotificationAction(
            identifier: Action.startConversation.rawValue,
            title: localizedString("notification_action_start_conversation"),
            options: [.foreground]
        )

        let dismiss = UNNotificationAction(
            identifier: Action.dismissAll.rawValue,
            title: localizedString("notification_action_dismiss"),
            options: [.destructive]
        )

        let nudgeCategory = UNNotificationCategory(
            identifier: Category.nudge.rawValue,
            actions: [start, dismiss],
            intentIdentifiers: [],
            options: [.customDismissAction]
        )

        let problemNudgeCategory = UNNotificationCategory(
            identifier: ProblemNotificationScheduler.Category.problemNudge.rawValue,
            actions: [start, dismiss],
            intentIdentifiers: [],
            options: [.customDismissAction]
        )

        center.setNotificationCategories([nudgeCategory, problemNudgeCategory])
    }

    // MARK: - Server-driven Nudge

    /// /mobile/nudge/trigger の応答を「即時ローカル通知」として提示
    func scheduleNudgeNow(nudgeId: String, domain: String, message: String, userInfo: [String: Any]) async {
        guard !nudgeId.isEmpty, !message.isEmpty else { return }

        let content = UNMutableNotificationContent()
        content.title = localizedString("app_name")
        content.body = message
        content.categoryIdentifier = Category.nudge.rawValue
        content.userInfo = userInfo
        content.sound = .default

        if #available(iOS 15.0, *) {
            let settings = await center.notificationSettings()
            content.interruptionLevel = (settings.timeSensitiveSetting == .enabled) ? .timeSensitive : .active
        }

        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: 1, repeats: false)
        let request = UNNotificationRequest(
            identifier: keyNudgeMain(nudgeId: nudgeId),
            content: content,
            trigger: trigger
        )

        do {
            try await center.add(request)
        } catch {
            logger.error("Failed to schedule nudge notification: \(error.localizedDescription, privacy: .public)")
        }
    }

    func nudgeId(fromIdentifier identifier: String) -> String? {
        let parts = identifier.split(separator: "_")
        guard parts.count >= 3, parts[0] == "NUDGE", parts[1] == "MAIN" else { return nil }
        return String(parts[2])
    }

    private func keyNudgeMain(nudgeId: String) -> String {
        "NUDGE_MAIN_\(nudgeId)"
    }
}
