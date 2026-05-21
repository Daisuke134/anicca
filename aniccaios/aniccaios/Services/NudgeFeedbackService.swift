import Foundation
import OSLog

/// Phase 7+8: Nudgeフィードバック送信サービス
/// hookFeedbackとcontentFeedbackを分離して送信
actor NudgeFeedbackService {
    static let shared = NudgeFeedbackService()

    private let logger = Logger(subsystem: "com.anicca.ios", category: "NudgeFeedbackService")

    /// UserDefaultsキー（DateはUserDefaultsに直接保存できないのでTimeIntervalを使用）
    private let scheduledNudgesKey = "scheduledNudges"

    /// 6時間（秒単位）
    private let expiredThresholdSeconds: TimeInterval = 6 * 60 * 60

    private init() {}

    // MARK: - Public Types

    struct FeedbackPayload: Encodable {
        let nudgeId: String
        let outcome: String
        let signals: Signals

        struct Signals: Encodable {
            let hookFeedback: String
            let contentFeedback: String?
            let timeSpentSeconds: Int?
        }
    }

    // MARK: - Public API

    /// フィードバックを送信
    func sendFeedback(
        nudgeId: String,
        hookFeedback: String,
        contentFeedback: String?,
        timeSpentSeconds: Int?
    ) async throws {
        let payload = FeedbackPayload(
            nudgeId: nudgeId,
            outcome: hookFeedback == "tapped" ? "success" : "ignored",
            signals: .init(
                hookFeedback: hookFeedback,
                contentFeedback: contentFeedback,
                timeSpentSeconds: timeSpentSeconds
            )
        )

        let url = await MainActor.run { AppConfig.nudgeFeedbackURL }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let deviceId = await AppState.shared.resolveDeviceId()
        request.setValue(deviceId, forHTTPHeaderField: "device-id")
        request.setValue(deviceId, forHTTPHeaderField: "user-id")

        request.httpBody = try JSONEncoder().encode(payload)

        let (_, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse,
              (200..<300).contains(httpResponse.statusCode) else {
            throw ServiceError.feedbackFailed
        }

        logger.info("✅ Feedback sent: \(nudgeId) hookFeedback=\(hookFeedback)")
    }

    /// アプリ起動時に6時間経過の未タップ通知を`ignored`として送信
    func sendIgnoredFeedbackForExpiredNudges() async {
        let expiredNudges = getExpiredUnrespondedNudges()

        for nudgeId in expiredNudges {
            do {
                try await sendFeedback(
                    nudgeId: nudgeId,
                    hookFeedback: "ignored",
                    contentFeedback: nil,
                    timeSpentSeconds: nil
                )
                markNudgeAsProcessed(nudgeId)
                logger.info("📤 Sent ignored feedback for expired nudge: \(nudgeId)")
            } catch {
                logger.error("Failed to send ignored feedback for \(nudgeId): \(error)")
            }
        }
    }

    /// 通知タップ時に呼び出し（UserDefaultsから削除してtappedを送信）
    func handleNudgeTapped(nudgeId: String) async throws {
        // UserDefaultsから削除（もうignoredとして送信しない）
        markNudgeAsProcessed(nudgeId)

        // tappedを送信
        try await sendFeedback(
            nudgeId: nudgeId,
            hookFeedback: "tapped",
            contentFeedback: nil,
            timeSpentSeconds: nil
        )
    }

    /// contentFeedback送信（👍👎タップ時）
    func sendContentFeedback(nudgeId: String, feedback: String, timeSpentSeconds: Int?) async throws {
        try await sendFeedback(
            nudgeId: nudgeId,
            hookFeedback: "tapped",
            contentFeedback: feedback,
            timeSpentSeconds: timeSpentSeconds
        )
    }

    // MARK: - Scheduled Nudge Management

    /// スケジュールされたNudgeを保存（ProblemNotificationSchedulerから呼び出し）
    func saveScheduledNudge(nudgeId: String, scheduledDate: Date) {
        var allScheduled = UserDefaults.standard.dictionary(forKey: scheduledNudgesKey) as? [String: TimeInterval] ?? [:]
        allScheduled[nudgeId] = scheduledDate.timeIntervalSince1970
        UserDefaults.standard.set(allScheduled, forKey: scheduledNudgesKey)
        logger.info("📅 Saved scheduled nudge: \(nudgeId) at \(scheduledDate)")
    }

    // MARK: - Private Methods

    /// 6時間経過の未タップNudgeを取得
    private func getExpiredUnrespondedNudges() -> [String] {
        let allScheduled = UserDefaults.standard.dictionary(forKey: scheduledNudgesKey) as? [String: TimeInterval] ?? [:]
        let now = Date().timeIntervalSince1970

        return allScheduled.compactMap { (nudgeId, scheduledTimestamp) in
            now - scheduledTimestamp > expiredThresholdSeconds ? nudgeId : nil
        }
    }

    /// Nudgeを処理済みとしてマーク（UserDefaultsから削除）
    private func markNudgeAsProcessed(_ nudgeId: String) {
        var allScheduled = UserDefaults.standard.dictionary(forKey: scheduledNudgesKey) as? [String: TimeInterval] ?? [:]
        allScheduled.removeValue(forKey: nudgeId)
        UserDefaults.standard.set(allScheduled, forKey: scheduledNudgesKey)
    }

    // MARK: - Test Helpers

    #if DEBUG
    /// テスト用: 期限切れNudgeを取得
    func getExpiredUnrespondedNudgesForTesting() -> [String] {
        return getExpiredUnrespondedNudges()
    }

    /// テスト用: Nudgeを処理済みとしてマーク
    func markNudgeAsProcessedForTesting(_ nudgeId: String) {
        markNudgeAsProcessed(nudgeId)
    }
    #endif

    // MARK: - Errors

    enum ServiceError: Error {
        case feedbackFailed
    }
}
