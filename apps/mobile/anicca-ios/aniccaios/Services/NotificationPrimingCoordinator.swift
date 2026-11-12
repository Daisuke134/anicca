import Foundation
import UserNotifications

/// Persists open-day / re-ask state for the second-chance notification
/// priming (feed) and decides whether it may be offered. Modeled on
/// `ReviewPromptCoordinator`, which owns the same job for review prompts.
@MainActor
final class NotificationPrimingCoordinator {
    static let shared = NotificationPrimingCoordinator()

    private let defaults: UserDefaults
    private let openDaysKey: String
    private let attemptsKey: String
    private let lastRepromptKey: String
    private let onboardingSkippedKey: String

    init(
        defaults: UserDefaults = .standard,
        openDaysKey: String = "com.anicca.notificationPriming.openDays",
        attemptsKey: String = "com.anicca.notificationPriming.attempts",
        lastRepromptKey: String = "com.anicca.notificationPriming.lastRepromptAt",
        onboardingSkippedKey: String = "com.anicca.notificationPriming.onboardingSkipped"
    ) {
        self.defaults = defaults
        self.openDaysKey = openDaysKey
        self.attemptsKey = attemptsKey
        self.lastRepromptKey = lastRepromptKey
        self.onboardingSkippedKey = onboardingSkippedKey
    }

    /// Call on app activation so distinct open days accumulate.
    func recordAppOpen(now: Date = Date(), calendar: Calendar = .current) {
        let existing = Set(defaults.stringArray(forKey: openDaysKey) ?? [])
        let updated = ReviewPromptPolicy.recordingOpenDay(
            existingDayKeys: existing,
            now: now,
            calendar: calendar
        )
        defaults.set(Array(updated).sorted(), forKey: openDaysKey)
    }

    /// Called when the user taps "Maybe later" on the onboarding priming.
    /// Kept for funnel segmentation; the re-ask gate itself keys off the
    /// live authorization status, so pre-1.9.12 skippers are covered too.
    func recordOnboardingSkipped() {
        defaults.set(true, forKey: onboardingSkippedKey)
    }

    var onboardingSkipped: Bool {
        defaults.bool(forKey: onboardingSkippedKey)
    }

    var distinctOpenDayCount: Int {
        (defaults.stringArray(forKey: openDaysKey) ?? []).count
    }

    var attemptsSoFar: Int {
        defaults.integer(forKey: attemptsKey)
    }

    var lastRepromptAt: Date? {
        let interval = defaults.double(forKey: lastRepromptKey)
        guard interval > 0 else { return nil }
        return Date(timeIntervalSince1970: interval)
    }

    /// Full gate for the feed value moment: policy limits plus the live
    /// authorization status must still be `.notDetermined`.
    func shouldOfferReprompt(
        now: Date = Date(),
        calendar: Calendar = .current
    ) async -> Bool {
        let launchArguments = ProcessInfo.processInfo.arguments
        if launchArguments.contains("UITESTING") || launchArguments.contains("-UITESTING") {
            return false
        }

        guard NotificationPrimingPolicy.shouldOfferReprompt(
            distinctOpenDayCount: distinctOpenDayCount,
            attemptsSoFar: attemptsSoFar,
            lastRepromptAt: lastRepromptAt,
            now: now,
            calendar: calendar
        ) else {
            return false
        }

        let status = await NotificationScheduler.shared.currentAuthorizationStatus()
        return status == .notDetermined
    }

    /// Record before presenting, so a dismissed sheet still counts toward
    /// the attempt cap and cooldown (same convention as the review prompt).
    func recordRepromptShown(now: Date = Date()) {
        defaults.set(attemptsSoFar + 1, forKey: attemptsKey)
        defaults.set(now.timeIntervalSince1970, forKey: lastRepromptKey)
    }
}
