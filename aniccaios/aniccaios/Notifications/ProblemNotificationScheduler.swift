import Foundation
import UserNotifications
import OSLog

/// テスト用プロトコル
protocol ProblemNotificationSchedulerProtocol {
    func scheduleNotifications(for problems: [String]) async
}

/// 問題ベースの通知スケジューラ
/// ユーザーが選択した問題に基づいて通知をスケジュール
final class ProblemNotificationScheduler: ProblemNotificationSchedulerProtocol {
    static let shared = ProblemNotificationScheduler()

    private let center = UNUserNotificationCenter.current()
    private let logger = Logger(subsystem: "com.anicca.ios", category: "ProblemNotificationScheduler")

    /// 通知カテゴリID
    enum Category: String {
        case problemNudge = "PROBLEM_NUDGE"
    }

    /// 最小通知間隔（分）
    private let minimumIntervalMinutes = 60

    /// cant_wake_upの起床ウィンドウ用間隔（分）: 06:00-06:30
    private let wakeWindowIntervalMinutes = 15
    
    /// Phase 5: 最大シフト量（分）- 2時間まで
    private let maxShiftMinutes = 120
    
    /// 現在のシフト量を保存するキー
    private let shiftStorageKey = "com.anicca.problemNotificationShifts"

    private init() {}

    // MARK: - Public API

    /// ユーザーの選択した問題に基づいて通知をスケジュール
    func scheduleNotifications(for problems: [String]) async {
        // Free/Pro分岐
        let isEntitled = await MainActor.run { AppState.shared.subscriptionInfo.isEntitled }
        if !isEntitled {
            // Free: always keep local free-plan nudges, even if APNs token is registered.
            // (Backend may gate remote problem nudges by entitlement; avoid notification blackout.)
            let freeIds = (0..<3).map { "free_nudge_\($0)" }
            center.removePendingNotificationRequests(withIdentifiers: freeIds)
            await removeAllProblemNotifications()
            FreePlanService.shared.scheduleFreePlanNudges(struggles: problems)
            return
        }

        // Entitled users: clear local problem notifications first (avoid duplicates).
        await removeAllProblemNotifications()

        // v1.6.3: APNs remote push is the primary delivery for entitled users.
        let forceLocal = ProcessInfo.processInfo.arguments.contains("-forceLocalProblemNotifications")
        if PushTokenService.shared.isRegistered && !forceLocal {
            logger.info("Remote Problem Push enabled; skip local scheduling")
            return
        }

        // Time Sensitive 設定チェック（計測用ログ）
        if #available(iOS 15.0, *) {
            let settings = await center.notificationSettings()
            if settings.timeSensitiveSetting == .disabled {
                logger.warning("Time Sensitive notifications are disabled by user. Nudges will not break through Focus modes.")
            }
        }

        // ★ 重要: Free プランかつ月間上限到達済みの場合はスケジュールしない
        let canSchedule = await MainActor.run { AppState.shared.canReceiveNudge }

        if !canSchedule {
            logger.info("Monthly nudge limit reached (Free plan). No notifications scheduled.")
            return
        }

        var allSchedules: [(time: (hour: Int, minute: Int), problem: ProblemType)] = []

        for problemRaw in problems {
            guard let problem = ProblemType(rawValue: problemRaw) else { continue }

            for time in problem.notificationSchedule {
                allSchedules.append((time: (time.hour, time.minute), problem: problem))
            }
        }

        // Sort by time (midnight-crossing slots treated as next day)
        allSchedules.sort { lhs, rhs in
            let lhsMin = lhs.time.hour < 6 ? lhs.time.hour * 60 + lhs.time.minute + 1440 : lhs.time.hour * 60 + lhs.time.minute
            let rhsMin = rhs.time.hour < 6 ? rhs.time.hour * 60 + rhs.time.minute + 1440 : rhs.time.hour * 60 + rhs.time.minute
            return lhsMin < rhsMin
        }

        // iOS limits pending notifications to 64. With 2-day window each slot uses up to 2.
        // Trim excess slots (latest chronological slots dropped first).
        let maxPendingNotifications = 64
        let maxSlots = maxPendingNotifications / 2  // 32 slots × 2 days = 64
        if allSchedules.count > maxSlots {
            logger.warning("Trimming \(allSchedules.count) slots to \(maxSlots) (iOS 64 limit)")
            allSchedules = Array(allSchedules.prefix(maxSlots))
        }

        // P4: usedVariants重複排除 / P5: Day1決定論的割り当て
        var usedVariantsPerProblem: [ProblemType: Set<Int>] = [:]
        var slotIndexPerProblem: [ProblemType: Int] = [:]
        var scheduledCount = 0

        // Day1判定（問題ごと）をMainActorで事前取得
        var isDay1PerProblem: [ProblemType: Bool] = [:]
        for schedule in allSchedules {
            let problem = schedule.problem
            if isDay1PerProblem[problem] == nil {
                isDay1PerProblem[problem] = await MainActor.run {
                    NudgeStatsManager.shared.isDay1(for: problem.rawValue)
                }
            }
        }

        for schedule in allSchedules {
            let hour = schedule.time.hour
            let minute = schedule.time.minute
            let problem = schedule.problem

            guard problem.isValidTime(hour: hour, minute: minute) else {
                logger.info("Skipped \(problem.rawValue) at \(hour):\(minute) - outside valid time range")
                continue
            }

            let slotIndex = slotIndexPerProblem[problem, default: 0]
            let usedVariants = usedVariantsPerProblem[problem, default: []]
            let isDay1 = isDay1PerProblem[problem] ?? false

            let variantIndex = await scheduleNotification(
                for: problem,
                hour: hour,
                minute: minute,
                slotIndex: slotIndex,
                usedVariants: usedVariants,
                isDay1: isDay1
            )

            // Track used variants for dedup
            if let idx = variantIndex {
                usedVariantsPerProblem[problem, default: []].insert(idx)
            }
            slotIndexPerProblem[problem] = slotIndex + 1
            scheduledCount += 1
        }

        logger.info("Scheduled \(scheduledCount) problem notifications (2-day window)")
    }

    /// すべての問題通知をキャンセル
    func cancelAllNotifications() async {
        await removeAllProblemNotifications()
    }

    #if DEBUG
    /// テスト用: 指定した問題の通知を5秒後に発火
    func testNotification(for problem: ProblemType) async {
        await testNotification(for: problem, scheduledHour: nil)
    }

    /// テスト用: 指定した問題・時刻の通知を5秒後に発火
    func testNotification(for problem: ProblemType, scheduledHour: Int?) async {
        // scheduledHour が指定されていれば、その時刻用のバリアントを選択
        let variantIndex: Int
        if let hour = scheduledHour {
            let selection = await MainActor.run {
                NudgeContentSelector.shared.selectVariant(for: problem, scheduledHour: hour)
            }
            variantIndex = selection.variantIndex
        } else {
            variantIndex = NudgeContent.contentForToday(for: problem).variantIndex
        }

        let notificationTextKey = "nudge_\(problem.rawValue)_notification_\(variantIndex + 1)"
        let detailTextKey = "nudge_\(problem.rawValue)_detail_\(variantIndex + 1)"

        let notificationContent = UNMutableNotificationContent()
        notificationContent.title = problem.notificationTitle
        notificationContent.body = NSLocalizedString(notificationTextKey, comment: "")
        notificationContent.categoryIdentifier = Category.problemNudge.rawValue
        notificationContent.sound = .default

        notificationContent.userInfo = [
            "problemType": problem.rawValue,
            "notificationTextKey": notificationTextKey,
            "detailTextKey": detailTextKey,
            "variantIndex": variantIndex,
            "scheduledHour": scheduledHour ?? 0,
            "scheduledMinute": 0
        ]

        if #available(iOS 15.0, *) {
            notificationContent.interruptionLevel = .active
        }

        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: 5, repeats: false)
        let identifier = "TEST_PROBLEM_\(problem.rawValue)_\(Date().timeIntervalSince1970)"
        let request = UNNotificationRequest(identifier: identifier, content: notificationContent, trigger: trigger)

        do {
            try await center.add(request)
            logger.info("Test notification scheduled for \(problem.rawValue) variant:\(variantIndex) hour:\(scheduledHour ?? -1)")
        } catch {
            logger.error("Failed to schedule test notification: \(error.localizedDescription)")
        }
    }
    #endif

    // MARK: - Private Methods

    /// v1.5.1: 2-day window + usedVariants + Day1 対応
    /// - Returns: 選択されたvariantIndex（usedVariantsトラッキング用）。LLMの場合はnil
    @discardableResult
    private func scheduleNotification(
        for problem: ProblemType,
        hour: Int,
        minute: Int,
        slotIndex: Int,
        usedVariants: Set<Int>,
        isDay1: Bool
    ) async -> Int? {
        // NudgeContentSelectorでバリアント選択（P4: usedVariants / P5: Day1）
        let selection = await MainActor.run {
            NudgeContentSelector.shared.selectVariant(
                for: problem,
                scheduledHour: hour,
                slotIndex: slotIndex,
                usedVariants: usedVariants,
                isDay1: isDay1
            )
        }

        let notificationContent = UNMutableNotificationContent()
        let titleKey = "problem_\(problem.rawValue)_notification_title"
        notificationContent.title = NSLocalizedString(titleKey, comment: "")
        notificationContent.categoryIdentifier = Category.problemNudge.rawValue
        notificationContent.sound = .default

        if selection.isAIGenerated, let llmNudge = selection.content {
            // LLM生成の場合
            notificationContent.body = llmNudge.hook
            notificationContent.userInfo = [
                "problemType": problem.rawValue,
                "isAIGenerated": true,
                "llmNudgeId": llmNudge.id,
                "notificationText": llmNudge.hook,
                "detailText": llmNudge.content,
                "scheduledHour": hour,
                "scheduledMinute": minute
            ]
        } else {
            // 既存バリアントの場合
            let notificationTextKey = "nudge_\(problem.rawValue)_notification_\(selection.variantIndex + 1)"
            let detailTextKey = "nudge_\(problem.rawValue)_detail_\(selection.variantIndex + 1)"
            notificationContent.body = NSLocalizedString(notificationTextKey, comment: "")
            notificationContent.userInfo = [
                "problemType": problem.rawValue,
                "isAIGenerated": false,
                "notificationTextKey": notificationTextKey,
                "detailTextKey": detailTextKey,
                "variantIndex": selection.variantIndex,
                "scheduledHour": hour,
                "scheduledMinute": minute
            ]
        }

        if #available(iOS 15.0, *) {
            let settings = await center.notificationSettings()
            notificationContent.interruptionLevel = (settings.timeSensitiveSetting == .enabled) ? .timeSensitive : .active
        }

        // P1: 2-day window — schedule for today (if not passed) and tomorrow
        let calendar = Calendar.current
        let now = Date()

        for dayOffset in 0...1 {
            guard let targetDay = calendar.date(byAdding: .day, value: dayOffset, to: now) else { continue }

            var dateComponents = calendar.dateComponents([.year, .month, .day], from: targetDay)
            dateComponents.hour = hour
            dateComponents.minute = minute

            // Skip if this time has already passed
            if let scheduledDate = calendar.date(from: dateComponents), scheduledDate <= now {
                continue
            }

            let trigger = UNCalendarNotificationTrigger(dateMatching: dateComponents, repeats: false)
            let identifier = "PROBLEM_\(problem.rawValue)_\(hour)_\(minute)_d\(dayOffset)"
            let request = UNNotificationRequest(
                identifier: identifier,
                content: notificationContent,
                trigger: trigger
            )

            do {
                try await center.add(request)
                logger.info("Scheduled \(problem.rawValue) at \(hour):\(minute) d\(dayOffset) variant:\(selection.variantIndex) ai:\(selection.isAIGenerated)")
            } catch {
                logger.error("Failed to schedule \(problem.rawValue) d\(dayOffset): \(error.localizedDescription)")
            }
        }

        // スケジュール成功時にNudgeStatsに記録（実際の配信時刻を渡す）
        let fireDate = calculateScheduledDate(hour: hour, minute: minute)
        await MainActor.run {
            NudgeStatsManager.shared.recordScheduled(
                problemType: problem.rawValue,
                variantIndex: selection.variantIndex,
                scheduledHour: hour,
                isAIGenerated: selection.isAIGenerated,
                llmNudgeId: selection.content?.id,
                fireDate: fireDate
            )
        }

        // Phase 7+8: LLM生成Nudgeの場合、scheduledNudgesに保存（ignored判定用）
        if let llmNudgeId = selection.content?.id {
            let scheduledDate = calculateScheduledDate(hour: hour, minute: minute)
            await NudgeFeedbackService.shared.saveScheduledNudge(nudgeId: llmNudgeId, scheduledDate: scheduledDate)
        }

        return selection.isAIGenerated ? nil : selection.variantIndex
    }

    private func removeAllProblemNotifications() async {
        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            center.getPendingNotificationRequests { requests in
                let identifiers = requests
                    .map(\.identifier)
                    .filter { $0.hasPrefix("PROBLEM_") }
                if !identifiers.isEmpty {
                    self.center.removePendingNotificationRequests(withIdentifiers: identifiers)
                }
                continuation.resume()
            }
        }
    }
    
    // MARK: - Wake Window Detection

    /// cant_wake_upの起床ウィンドウ（06:00-06:30）かどうか判定
    func isWakeWindow(problem: ProblemType, hour: Int, minute: Int) -> Bool {
        guard problem == .cantWakeUp else { return false }
        let totalMinutes = hour * 60 + minute
        return totalMinutes >= 360 && totalMinutes <= 390 // 06:00-06:30
    }

    // MARK: - Phase 7+8: Scheduled Date Calculation

    /// スケジュール予定時刻を計算
    private func calculateScheduledDate(hour: Int, minute: Int) -> Date {
        let calendar = Calendar.current
        var components = calendar.dateComponents([.year, .month, .day], from: Date())
        components.hour = hour
        components.minute = minute

        guard let scheduledDate = calendar.date(from: components) else {
            return Date()
        }

        // 過去の時刻なら翌日として扱う
        if scheduledDate < Date() {
            return calendar.date(byAdding: .day, value: 1, to: scheduledDate) ?? scheduledDate
        }
        return scheduledDate
    }

    // MARK: - Phase 5: Shift Calculation (Testable)

    /// シフト量を計算（純粋関数、テスト可能）
    /// - Parameters:
    ///   - currentShift: 現在のシフト量（分）
    ///   - consecutiveIgnored: 連続無視日数
    /// - Returns: 新しいシフト量（分）、最大 maxShiftMinutes まで
    func calculateNewShift(currentShift: Int, consecutiveIgnored: Int) -> Int {
        guard consecutiveIgnored >= 2 else { return currentShift }
        return min(currentShift + 30, maxShiftMinutes)
    }

    // MARK: - Phase 5: Shift Management

    /// 現在のシフト量を取得
    private func getCurrentShiftMinutes(problemType: String, originalHour: Int) -> Int {
        let key = "\(problemType)_\(originalHour)"
        let shifts = UserDefaults.standard.dictionary(forKey: shiftStorageKey) as? [String: Int] ?? [:]
        return shifts[key] ?? 0
    }
    
    /// シフト量を保存
    private func recordShift(problemType: String, originalHour: Int, shiftMinutes: Int) {
        let key = "\(problemType)_\(originalHour)"
        var shifts = UserDefaults.standard.dictionary(forKey: shiftStorageKey) as? [String: Int] ?? [:]
        shifts[key] = shiftMinutes
        UserDefaults.standard.set(shifts, forKey: shiftStorageKey)
    }
    
    /// シフト量をリセット（タップ時に呼び出す）
    func resetShift(for problemType: String, originalHour: Int) {
        let key = "\(problemType)_\(originalHour)"
        var shifts = UserDefaults.standard.dictionary(forKey: shiftStorageKey) as? [String: Int] ?? [:]
        shifts.removeValue(forKey: key)
        UserDefaults.standard.set(shifts, forKey: shiftStorageKey)
        logger.info("Reset shift for \(problemType) at hour \(originalHour)")
    }
    
    #if DEBUG
    /// デバッグ用: 全シフトをリセット
    func resetAllShifts() {
        UserDefaults.standard.removeObject(forKey: shiftStorageKey)
        logger.info("All shifts reset")
    }
    
    /// デバッグ用: シフト状態を取得
    func getAllShifts() -> [String: Int] {
        return UserDefaults.standard.dictionary(forKey: shiftStorageKey) as? [String: Int] ?? [:]
    }
    #endif

    // MARK: - Notification Parsing

    /// 通知からNudgeContentを復元
    static func nudgeContent(from userInfo: [AnyHashable: Any]) -> NudgeContent? {
        guard let problemRaw = userInfo["problemType"] as? String,
              let problem = ProblemType(rawValue: problemRaw) else {
            return nil
        }

        // LLM生成Nudgeの場合
        if let isAIGenerated = userInfo["isAIGenerated"] as? Bool, isAIGenerated,
           let llmNudgeId = userInfo["llmNudgeId"] as? String,
           let notificationText = userInfo["notificationText"] as? String,
           let detailText = userInfo["detailText"] as? String {
            return NudgeContent(
                problemType: problem,
                notificationText: notificationText,
                detailText: detailText,
                variantIndex: -1,
                isAIGenerated: true,
                llmNudgeId: llmNudgeId
            )
        }

        // 既存バリアント: キーから解決
        if let variantIndex = userInfo["variantIndex"] as? Int,
           let notificationTextKey = userInfo["notificationTextKey"] as? String,
           let detailTextKey = userInfo["detailTextKey"] as? String {
            let notificationText = NSLocalizedString(notificationTextKey, comment: "")
            let detailText = NSLocalizedString(detailTextKey, comment: "")

            return NudgeContent(
                problemType: problem,
                notificationText: notificationText,
                detailText: detailText,
                variantIndex: variantIndex,
                isAIGenerated: false,
                llmNudgeId: nil
            )
        }

        // 後方互換: 古い形式（文字列直接保存）
        if let variantIndex = userInfo["variantIndex"] as? Int,
           let notificationText = userInfo["notificationText"] as? String,
           let detailText = userInfo["detailText"] as? String {
            return NudgeContent(
                problemType: problem,
                notificationText: notificationText,
                detailText: detailText,
                variantIndex: variantIndex,
                isAIGenerated: false,
                llmNudgeId: nil
            )
        }

        return nil
    }

    /// 通知がProblem Nudgeかどうか判定
    static func isProblemNudge(identifier: String) -> Bool {
        return identifier.hasPrefix("PROBLEM_") || identifier.hasPrefix("TEST_PROBLEM_")
    }
}
