import Testing
@testable import aniccaios

struct NudgeFeedbackServiceTests {

    // MARK: - Expired Nudge Detection Tests

    @Test("Get expired unresponded nudges returns empty when no nudges scheduled")
    func test_getExpiredUnrespondedNudges_empty() async {
        // UserDefaultsをクリア
        UserDefaults.standard.removeObject(forKey: "scheduledNudges")

        let expiredNudges = await NudgeFeedbackService.shared.getExpiredUnrespondedNudgesForTesting()
        #expect(expiredNudges.isEmpty)
    }

    @Test("Get expired unresponded nudges returns expired nudges")
    func test_getExpiredUnrespondedNudges_returnsExpired() async {
        // 7時間前のNudgeを登録（6時間経過で期限切れ）
        let sevenHoursAgo = Date().timeIntervalSince1970 - (7 * 60 * 60)
        let scheduledNudges: [String: TimeInterval] = [
            "expired-nudge-1": sevenHoursAgo,
            "expired-nudge-2": sevenHoursAgo
        ]
        UserDefaults.standard.set(scheduledNudges, forKey: "scheduledNudges")

        let expiredNudges = await NudgeFeedbackService.shared.getExpiredUnrespondedNudgesForTesting()

        #expect(expiredNudges.count == 2)
        #expect(expiredNudges.contains("expired-nudge-1"))
        #expect(expiredNudges.contains("expired-nudge-2"))

        // クリーンアップ
        UserDefaults.standard.removeObject(forKey: "scheduledNudges")
    }

    @Test("Get expired unresponded nudges ignores non-expired nudges")
    func test_getExpiredUnrespondedNudges_ignoresNonExpired() async {
        // 1時間前のNudge（まだ期限切れではない）
        let oneHourAgo = Date().timeIntervalSince1970 - (1 * 60 * 60)
        let scheduledNudges: [String: TimeInterval] = [
            "fresh-nudge": oneHourAgo
        ]
        UserDefaults.standard.set(scheduledNudges, forKey: "scheduledNudges")

        let expiredNudges = await NudgeFeedbackService.shared.getExpiredUnrespondedNudgesForTesting()

        #expect(expiredNudges.isEmpty)

        // クリーンアップ
        UserDefaults.standard.removeObject(forKey: "scheduledNudges")
    }

    // MARK: - Mark Nudge as Processed Tests

    @Test("Mark nudge as processed removes it from scheduled nudges")
    func test_markNudgeAsProcessed_removesFromScheduled() async {
        let nudgeId = "test-nudge-123"
        let now = Date().timeIntervalSince1970
        let scheduledNudges: [String: TimeInterval] = [
            nudgeId: now,
            "other-nudge": now
        ]
        UserDefaults.standard.set(scheduledNudges, forKey: "scheduledNudges")

        await NudgeFeedbackService.shared.markNudgeAsProcessedForTesting(nudgeId)

        let remaining = UserDefaults.standard.dictionary(forKey: "scheduledNudges") as? [String: TimeInterval] ?? [:]
        #expect(remaining[nudgeId] == nil)
        #expect(remaining["other-nudge"] != nil)

        // クリーンアップ
        UserDefaults.standard.removeObject(forKey: "scheduledNudges")
    }

    // MARK: - FeedbackPayload Tests

    @Test("FeedbackPayload encodes correctly")
    func test_feedbackPayload_encodes() throws {
        let payload = NudgeFeedbackService.FeedbackPayload(
            nudgeId: "test-123",
            outcome: "success",
            signals: .init(
                hookFeedback: "tapped",
                contentFeedback: "thumbsUp",
                timeSpentSeconds: 15
            )
        )

        let data = try JSONEncoder().encode(payload)
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]

        #expect(json?["nudgeId"] as? String == "test-123")
        #expect(json?["outcome"] as? String == "success")

        let signals = json?["signals"] as? [String: Any]
        #expect(signals?["hookFeedback"] as? String == "tapped")
        #expect(signals?["contentFeedback"] as? String == "thumbsUp")
        #expect(signals?["timeSpentSeconds"] as? Int == 15)
    }

    @Test("FeedbackPayload encodes with null contentFeedback")
    func test_feedbackPayload_nullContentFeedback() throws {
        let payload = NudgeFeedbackService.FeedbackPayload(
            nudgeId: "test-456",
            outcome: "ignored",
            signals: .init(
                hookFeedback: "ignored",
                contentFeedback: nil,
                timeSpentSeconds: nil
            )
        )

        let data = try JSONEncoder().encode(payload)
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]

        #expect(json?["nudgeId"] as? String == "test-456")
        #expect(json?["outcome"] as? String == "ignored")
    }
}
