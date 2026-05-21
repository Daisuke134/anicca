import XCTest
@testable import CalmCortisol

final class CalmCortisolTests: XCTestCase {
    func testBreathingTypeCycleDuration() {
        XCTAssertEqual(BreathingType.box.totalCycleDuration, 16)
        XCTAssertEqual(BreathingType.fourSevenEight.totalCycleDuration, 19)
        XCTAssertEqual(BreathingType.physiologicalSigh.totalCycleDuration, 11)
    }

    func testSessionStoreToday() {
        // Given
        let store = SessionStore.shared
        let initialCount = store.todayCount()

        // When
        let record = SessionRecord(breathingType: .box, durationSec: 60)
        store.save(record)

        // Then
        XCTAssertEqual(store.todayCount(), initialCount + 1)
    }

    func testLocalization() {
        // L10n should return non-empty strings
        XCTAssertFalse(L10n.onboardingWelcomeTitle.isEmpty)
        XCTAssertFalse(L10n.paywallCTA.isEmpty)
        XCTAssertFalse(L10n.settingsTitle.isEmpty)
    }
}
