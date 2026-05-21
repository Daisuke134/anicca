import Foundation

enum Constants {
    static let defaultWorkIntervalMinutes = 20
    static let defaultBreakDurationSeconds = 20
    static let defaultWorkIntervalSeconds = defaultWorkIntervalMinutes * 60
    static let hasCompletedOnboardingKey = "hasCompletedOnboarding"
    static let timerIntervalMinutesKey = "timerIntervalMinutes"
    static let breakDurationSecondsKey = "breakDurationSeconds"
    static let notificationsEnabledKey = "notificationsEnabled"
    static let todayBreakCountKey = "todayBreakCount"
    static let currentStreakKey = "currentStreak"
    static let lastActiveDateKey = "lastActiveDate"
    static let scheduleStartHourKey = "scheduleStartHour"
    static let scheduleEndHourKey = "scheduleEndHour"
    static let scheduleEnabledKey = "scheduleEnabled"
}
