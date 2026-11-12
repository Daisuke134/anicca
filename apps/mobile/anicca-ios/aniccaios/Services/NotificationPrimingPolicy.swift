import Foundation

/// Decides when a second-chance notification priming may be offered in the feed.
///
/// Context (anicca-ops Issue #48): the winner-pattern onboarding flow —
/// goal → first affirmation → reminder schedule → priming screen → system
/// dialog — shipped in 1.9.11, but a user who taps "Maybe later" on the
/// onboarding priming keeps `authorizationStatus == .notDetermined` and was
/// never asked again. Winners re-ask after value has been proven instead of
/// relying on the single onboarding moment.
///
/// Rules:
/// - Require opens on at least `minimumDistinctOpenDays` distinct calendar
///   days, so the re-ask lands on a return visit, never in the first session.
/// - At most `maximumAttempts` lifetime re-asks, spaced by `cooldownDays`.
/// - The caller must additionally verify the live authorization status is
///   `.notDetermined`: users who denied in the system dialog cannot be
///   re-asked, and users who already granted do not need it.
struct NotificationPrimingPolicy: Sendable {
    static let minimumDistinctOpenDays = 2
    static let cooldownDays = 30
    static let maximumAttempts = 2

    /// Pure gate used at a value moment. Does not mutate storage.
    static func shouldOfferReprompt(
        distinctOpenDayCount: Int,
        attemptsSoFar: Int,
        lastRepromptAt: Date?,
        now: Date = Date(),
        calendar: Calendar = .current
    ) -> Bool {
        guard distinctOpenDayCount >= minimumDistinctOpenDays else { return false }
        guard attemptsSoFar < maximumAttempts else { return false }

        if let last = lastRepromptAt {
            guard let eligibleAt = calendar.date(byAdding: .day, value: cooldownDays, to: last) else {
                return false
            }
            guard now >= eligibleAt else { return false }
        }

        return true
    }
}
