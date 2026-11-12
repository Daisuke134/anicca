import XCTest
@testable import aniccaios

final class NotificationPrimingPolicyTests: XCTestCase {

    private var calendar: Calendar {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(secondsFromGMT: 0)!
        return cal
    }

    private func date(_ year: Int, _ month: Int, _ day: Int, hour: Int = 12) -> Date {
        calendar.date(from: DateComponents(year: year, month: month, day: day, hour: hour))!
    }

    // MARK: - shouldOfferReprompt

    func test_shouldOffer_false_inFirstSession_oneDay() {
        XCTAssertFalse(
            NotificationPrimingPolicy.shouldOfferReprompt(
                distinctOpenDayCount: 1,
                attemptsSoFar: 0,
                lastRepromptAt: nil,
                now: date(2026, 11, 12),
                calendar: calendar
            )
        )
    }

    func test_shouldOffer_true_onReturnVisit_neverAsked() {
        XCTAssertTrue(
            NotificationPrimingPolicy.shouldOfferReprompt(
                distinctOpenDayCount: 2,
                attemptsSoFar: 0,
                lastRepromptAt: nil,
                now: date(2026, 11, 12),
                calendar: calendar
            )
        )
    }

    func test_shouldOffer_false_within30DayCooldown() {
        XCTAssertFalse(
            NotificationPrimingPolicy.shouldOfferReprompt(
                distinctOpenDayCount: 5,
                attemptsSoFar: 1,
                lastRepromptAt: date(2026, 10, 14), // 29 days before
                now: date(2026, 11, 12),
                calendar: calendar
            )
        )
    }

    func test_shouldOffer_true_after30DayCooldown() {
        XCTAssertTrue(
            NotificationPrimingPolicy.shouldOfferReprompt(
                distinctOpenDayCount: 5,
                attemptsSoFar: 1,
                lastRepromptAt: date(2026, 10, 13), // exactly 30 days before
                now: date(2026, 11, 12),
                calendar: calendar
            )
        )
    }

    func test_shouldOffer_false_atAttemptCap() {
        XCTAssertFalse(
            NotificationPrimingPolicy.shouldOfferReprompt(
                distinctOpenDayCount: 10,
                attemptsSoFar: NotificationPrimingPolicy.maximumAttempts,
                lastRepromptAt: date(2026, 1, 1),
                now: date(2026, 11, 12),
                calendar: calendar
            )
        )
    }

    // MARK: - Coordinator state (injected defaults)

    @MainActor
    func test_coordinator_recordsOpenDaysAttemptsAndSkip() {
        let suite = "NotificationPrimingPolicyTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }

        let coordinator = NotificationPrimingCoordinator(
            defaults: defaults,
            openDaysKey: "openDays",
            attemptsKey: "attempts",
            lastRepromptKey: "lastReprompt",
            onboardingSkippedKey: "skipped"
        )

        XCTAssertEqual(coordinator.distinctOpenDayCount, 0)
        coordinator.recordAppOpen(now: date(2026, 11, 11), calendar: calendar)
        coordinator.recordAppOpen(now: date(2026, 11, 11, hour: 23), calendar: calendar)
        XCTAssertEqual(coordinator.distinctOpenDayCount, 1)
        coordinator.recordAppOpen(now: date(2026, 11, 12), calendar: calendar)
        XCTAssertEqual(coordinator.distinctOpenDayCount, 2)

        XCTAssertEqual(coordinator.attemptsSoFar, 0)
        XCTAssertNil(coordinator.lastRepromptAt)
        coordinator.recordRepromptShown(now: date(2026, 11, 12))
        XCTAssertEqual(coordinator.attemptsSoFar, 1)
        XCTAssertEqual(coordinator.lastRepromptAt, date(2026, 11, 12))

        XCTAssertFalse(coordinator.onboardingSkipped)
        coordinator.recordOnboardingSkipped()
        XCTAssertTrue(coordinator.onboardingSkipped)
    }
}
