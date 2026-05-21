import Foundation
import OSLog
import UserNotifications

/// v0.3: /mobile/nudge/trigger -> (必要なら) ローカル通知を提示
/// - 1.6.2 SSOT: センサー前提ではなく、基本は「固定スケジュール + サーバ主導（/pending）」で運用する。
/// - /trigger は互換/デバッグ用途（E2E検証）として残す。
@MainActor
final class NudgeTriggerService {
    static let shared = NudgeTriggerService()

    private let logger = Logger(subsystem: "com.anicca.ios", category: "NudgeTrigger")
    private let iso8601: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    private init() {}

    // MARK: - Event Types (debug + legacy)
    enum EventType: String {
        // E2E / debug (no sensors)
        case e2ePause = "e2e_pause"

        // Legacy sensor-style names (kept for backward compatibility)
        case sns30Min = "sns_30min"
        case sns60Min = "sns_60min"
        case sedentary2h = "sedentary_2h"
        case morningPhone = "morning_phone"
        case bedtimePre = "bedtime_pre"
        case wakeAlarmFired = "wake_alarm_fired"
        case feeling = "feeling" // Feeling EMI DP（Mental）
    }

    // MARK: - Public entrypoints
    func trigger(eventType: EventType, payload: [String: Any] = [:]) async {
        // v0.4+: allow anonymous users (fallback to deviceId), since backend supports legacy headers.
        let userId: String
        if case .signedIn(let credentials) = AppState.shared.authStatus {
            userId = credentials.userId
        } else {
            userId = AppState.shared.resolveDeviceId()
        }

        var req = URLRequest(url: AppConfig.nudgeTriggerURL)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue(AppState.shared.resolveDeviceId(), forHTTPHeaderField: "device-id")
        req.setValue(userId, forHTTPHeaderField: "user-id")

        var body: [String: Any] = [
            "eventType": eventType.rawValue,
            "timestamp": iso8601.string(from: Date())
        ]
        if !payload.isEmpty { body["payload"] = payload }

        do {
            req.httpBody = try JSONSerialization.data(withJSONObject: body)
            let (data, response) = try await NetworkSessionManager.shared.session.data(for: req)
            guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
                logger.error("nudge/trigger failed: non-2xx")
                return
            }

            // 期待レスポンス（migration-patch-v3.md 6.4）
            // {
            //   "nudgeId": "uuid",
            //   "templateId": "...",
            //   "message": "...",
            //   "domain": "wake|screen|movement|mental|habit|morning_phone|sleep"
            // }
            guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }
            let nudgeId = (json["nudgeId"] as? String) ?? ""
            let message = (json["message"] as? String) ?? ""
            let domain = (json["domain"] as? String) ?? ""

            // サーバが do_nothing / 空メッセージを返した場合は通知しない（送信可否はサーバ責務）
            guard !nudgeId.isEmpty, !message.isEmpty else {
                return
            }

            await NotificationScheduler.shared.scheduleNudgeNow(
                nudgeId: nudgeId,
                domain: domain,
                message: message,
                userInfo: [
                    "nudgeId": nudgeId,
                    "domain": domain,
                    "eventType": eventType.rawValue
                ]
            )
        } catch {
            logger.error("nudge/trigger error: \(error.localizedDescription, privacy: .public)")
        }
    }

    /// Wake DP (legacy)
    func triggerWakeAlarmFired() async {
        await trigger(eventType: .wakeAlarmFired)
    }

    // MARK: - Feedback (minimum signals in v0.3)
    enum FeedbackOutcome: String {
        case success
        case failed
        case ignored
    }

    func sendFeedback(nudgeId: String, outcome: FeedbackOutcome, signals: [String: Any]) async {
        guard !nudgeId.isEmpty else { return }
        guard case .signedIn(let credentials) = AppState.shared.authStatus else { return }

        var req = URLRequest(url: AppConfig.nudgeFeedbackURL)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue(AppState.shared.resolveDeviceId(), forHTTPHeaderField: "device-id")
        req.setValue(credentials.userId, forHTTPHeaderField: "user-id")

        let body: [String: Any] = [
            "nudgeId": nudgeId,
            "outcome": outcome.rawValue,
            "signals": signals
        ]

        do {
            req.httpBody = try JSONSerialization.data(withJSONObject: body)
            _ = try await NetworkSessionManager.shared.session.data(for: req)
        } catch {
            logger.error("nudge/feedback error: \(error.localizedDescription, privacy: .public)")
        }
    }

    // MARK: - Notification signals (called from AppDelegate)
    func recordOpened(nudgeId: String, actionIdentifier: String) async {
        await sendFeedback(
            nudgeId: nudgeId,
            outcome: .success, // v0.3: 「開封」は最低限の成功シグナルとして success 扱い（追加の成功/失敗確定はセンサー実装後に拡張）
            signals: [
                "notificationOpened": true,
                "actionIdentifier": actionIdentifier
            ]
        )
    }

    func recordDismissed(nudgeId: String) async {
        await sendFeedback(
            nudgeId: nudgeId,
            outcome: .ignored,
            signals: [
                "notificationOpened": false
            ]
        )
    }
}
