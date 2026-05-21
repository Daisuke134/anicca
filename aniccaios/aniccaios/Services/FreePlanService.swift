import Foundation
import UserNotifications

final class FreePlanService {
    static let shared = FreePlanService()
    static let dailyLimit = 3

    private let calendar: Calendar
    private let nowProvider: () -> Date
    private let notificationCenter: UNUserNotificationCenter
    private let defaults: UserDefaults

    init(
        calendar: Calendar = .current,
        nowProvider: @escaping () -> Date = { Date() },
        notificationCenter: UNUserNotificationCenter = .current(),
        defaults: UserDefaults = .standard
    ) {
        self.calendar = calendar
        self.nowProvider = nowProvider
        self.notificationCenter = notificationCenter
        self.defaults = defaults
    }

    private let slots: [(hour: Int, minute: Int)] = [
        (8, 0),   // 朝
        (12, 30), // 昼
        (20, 0)   // 夜
    ]

    func nextScheduledNudgeTimes() -> [Date] {
        let now = nowProvider()
        return slots.compactMap { slot in
            var components = calendar.dateComponents([.year, .month, .day], from: now)
            components.hour = slot.hour
            components.minute = slot.minute
            return calendar.date(from: components)
        }.filter { $0 > nowProvider() }
    }

    func problemForSlot(day: Int, slot: Int, problems: [ProblemType]) -> ProblemType? {
        guard !problems.isEmpty else { return nil }
        let index = (day - 1 + slot) % problems.count
        return problems[index]
    }

    func scheduleFreePlanNudges(struggles: [String]) {
        let problems = struggles.compactMap { ProblemType(rawValue: $0) }
        scheduleFreePlanNudges(problems: problems)
    }

    func scheduleFreePlanNudges(problems: [ProblemType]) {
        guard !problems.isEmpty else {
            print("[FreePlanService] No problems selected, skipping schedule")
            return
        }

        // 既存のFree Plan通知を削除
        notificationCenter.removePendingNotificationRequests(withIdentifiers:
            (0..<Self.dailyLimit).map { "free_nudge_\($0)" }
        )

        let today = nowProvider()
        let now = today

        for (index, slot) in slots.enumerated() {
            var targetDay = today
            var dateComponents = calendar.dateComponents([.year, .month, .day], from: targetDay)
            dateComponents.hour = slot.hour
            dateComponents.minute = slot.minute

            if let scheduledDate = calendar.date(from: dateComponents), scheduledDate <= now {
                // 過去時刻: 翌日にシフト
                targetDay = calendar.date(byAdding: .day, value: 1, to: today) ?? today
                dateComponents = calendar.dateComponents([.year, .month, .day], from: targetDay)
                dateComponents.hour = slot.hour
                dateComponents.minute = slot.minute
            }

            let rotationDay = calendar.ordinality(of: .day, in: .year, for: targetDay) ?? 1
            guard let problem = problemForSlot(day: rotationDay, slot: index, problems: problems) else {
                continue
            }

            let content = UNMutableNotificationContent()
            content.title = problem.notificationTitle
            content.body = NudgeContent.notificationMessages(for: problem).first ?? ""
            content.sound = .default
            content.userInfo = [
                "problemType": problem.rawValue,
                "isRuleBased": true,
                "tier": "free"
            ]

            let trigger = UNCalendarNotificationTrigger(dateMatching: dateComponents, repeats: false)

            let request = UNNotificationRequest(
                identifier: "free_nudge_\(index)",
                content: content,
                trigger: trigger
            )
            notificationCenter.add(request)
        }

        let todayDayOfYear = calendar.ordinality(of: .day, in: .year, for: today) ?? 1
        defaults.set(todayDayOfYear, forKey: "freePlanLastScheduledDay")
        print("[FreePlanService] Scheduled nudges, saved day=\(todayDayOfYear)")
    }

    func rescheduleIfNeeded(problems: [ProblemType]) {
        let today = nowProvider()
        let currentDay = calendar.ordinality(of: .day, in: .year, for: today) ?? 1
        let lastDay = defaults.integer(forKey: "freePlanLastScheduledDay")

        if currentDay != lastDay {
            scheduleFreePlanNudges(problems: problems)
        }
    }
}
