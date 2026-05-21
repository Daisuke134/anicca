import Foundation
import SwiftData

@Model
final class PlungeSession {
    var id: UUID
    var date: Date
    var duration: TimeInterval
    var waterTemperature: Double?
    var hotTemperature: Double?
    var notes: String
    var heartRateAvg: Double?
    var heartRateMax: Double?
    var heartRates: [Double]
    var protocolName: String?
    var isContrastSession: Bool
    var coldDuration: TimeInterval?
    var hotDuration: TimeInterval?
    var roundsCompleted: Int?
    var createdAt: Date

    init(duration: TimeInterval, waterTemperature: Double? = nil, notes: String = "") {
        self.id = UUID()
        self.date = Date()
        self.duration = duration
        self.waterTemperature = waterTemperature
        self.notes = notes
        self.heartRates = []
        self.isContrastSession = false
        self.createdAt = Date()
    }
}

enum AccessibilityID {
    // Onboarding (SCR-001 to SCR-003)
    static let onboardingGetStarted = "onboarding_get_started"
    static let onboardingExperienceBeginner = "onboarding_experience_beginner"
    static let onboardingExperienceIntermediate = "onboarding_experience_intermediate"
    static let onboardingExperienceAdvanced = "onboarding_experience_advanced"
    static let onboardingContinue = "onboarding_continue"
    static let onboardingEnableNotifications = "onboarding_enable_notifications"
    static let onboardingSkipNotifications = "onboarding_skip_notifications"

    // Paywall (SCR-004)
    static let paywallView = "paywall_view"
    static let paywallHeadline = "paywall_headline"
    static let paywallPlanWeekly = "paywall_plan_weekly"
    static let paywallPlanMonthly = "paywall_plan_monthly"
    static let paywallPlanAnnual = "paywall_plan_annual"
    static let paywallCta = "paywall_cta"
    static let paywallMaybeLater = "paywall_maybe_later"
    static let paywallRestore = "paywall_restore"

    // Timer (SCR-005)
    static let timerView = "timer_view"
    static let circularTimer = "circular_timer"
    static let timerStart = "timer_start"
    static let timerPause = "timer_pause"
    static let timerStop = "timer_stop"
    static let timerBreathingPrep = "timer_breathing_prep"
    static let timerProtocolSelector = "timer_protocol_selector"
    static let timerTemperatureInput = "timer_temperature_input"
    static let timerHrDisplay = "timer_hr_display"

    // Breathing (SCR-006)
    static let breathingCircle = "breathing_circle"
    static let breathingPhaseLabel = "breathing_phase_label"
    static let breathingSkip = "breathing_skip"

    // Session Summary (SCR-007)
    static let sessionSummaryView = "session_summary_view"
    static let sessionSummaryDuration = "session_summary_duration"
    static let sessionSummaryTemp = "session_summary_temp"
    static let sessionSummaryHr = "session_summary_hr"
    static let sessionSummaryNotes = "session_summary_notes"
    static let sessionSummarySave = "session_summary_save"

    // History (SCR-008)
    static let historyView = "history_view"
    static let historySearch = "history_search"
    static let sessionCard = "session_card"
    static let historyUpgradeBanner = "history_upgrade_banner"

    // Session Detail (SCR-009)
    static let sessionDetailView = "session_detail_view"

    // Progress (SCR-010)
    static let progressView = "progress_view"
    static let streakCalendar = "streak_calendar"
    static let streakCurrent = "streak_current"
    static let streakLongest = "streak_longest"
    static let progressDurationChart = "progress_duration_chart"

    // Settings (SCR-011)
    static let settingsView = "settings_view"
    static let settingsTempUnit = "settings_temp_unit"
    static let settingsNotifications = "settings_notifications"
    static let settingsUpgrade = "settings_upgrade"
    static let settingsRestore = "settings_restore"
    static let settingsPrivacy = "settings_privacy"

    // Tab Bar
    static let tabTimer = "tab_timer"
    static let tabHistory = "tab_history"
    static let tabProgress = "tab_progress"
    static let tabSettings = "tab_settings"
}
