// OnboardingStepMigrationTests.swift
// v4 (Bible-compliant 20-step) onboarding enum + v2→v4 migration tests

import XCTest
@testable import aniccaios

final class OnboardingStepMigrationTests: XCTestCase {

    // MARK: - v4 Enum Raw Values (20-step)

    func test_welcome_rawValue_is0() {
        XCTAssertEqual(OnboardingStep.welcome.rawValue, 0)
    }

    func test_name_rawValue_is1() {
        XCTAssertEqual(OnboardingStep.name.rawValue, 1)
    }

    func test_age_rawValue_is2() {
        XCTAssertEqual(OnboardingStep.age.rawValue, 2)
    }

    func test_goal_rawValue_is3() {
        XCTAssertEqual(OnboardingStep.goal.rawValue, 3)
    }

    func test_painPoints_rawValue_is4() {
        XCTAssertEqual(OnboardingStep.painPoints.rawValue, 4)
    }

    func test_notifications_rawValue_is19() {
        XCTAssertEqual(OnboardingStep.notifications.rawValue, 19)
    }

    func test_allCases_count_is20() {
        XCTAssertEqual(OnboardingStep.allCases.count, 20)
    }

    // MARK: - v2 (8-step) → v4 (20-step) Migration

    func test_v2Migration_0_mapsTo_welcome() {
        XCTAssertEqual(OnboardingStep.migratedFromV2RawValue(0), .welcome)
    }

    func test_v2Migration_1_mapsTo_painPoints() {
        XCTAssertEqual(OnboardingStep.migratedFromV2RawValue(1), .painPoints)
    }

    func test_v2Migration_2_mapsTo_struggleFreq() {
        XCTAssertEqual(OnboardingStep.migratedFromV2RawValue(2), .struggleFreq)
    }

    func test_v2Migration_3_mapsTo_planReveal() {
        XCTAssertEqual(OnboardingStep.migratedFromV2RawValue(3), .planReveal)
    }

    func test_v2Migration_4_mapsTo_processing() {
        XCTAssertEqual(OnboardingStep.migratedFromV2RawValue(4), .processing)
    }

    func test_v2Migration_5_mapsTo_valueDelivery() {
        XCTAssertEqual(OnboardingStep.migratedFromV2RawValue(5), .valueDelivery)
    }

    func test_v2Migration_6_mapsTo_appDemo() {
        XCTAssertEqual(OnboardingStep.migratedFromV2RawValue(6), .appDemo)
    }

    func test_v2Migration_7_mapsTo_notifications() {
        XCTAssertEqual(OnboardingStep.migratedFromV2RawValue(7), .notifications)
    }

    func test_v2Migration_outOfRange_returnsNil() {
        XCTAssertNil(OnboardingStep.migratedFromV2RawValue(999))
        XCTAssertNil(OnboardingStep.migratedFromV2RawValue(-1))
    }

    // MARK: - Progress Bar Formula (R2)

    func test_progressBar_welcome_is20pct() {
        XCTAssertEqual(OnboardingProgressBar.progress(for: .welcome), 0.2, accuracy: 0.001)
    }

    func test_progressBar_notifications_is80pct() {
        XCTAssertEqual(OnboardingProgressBar.progress(for: .notifications), 0.8, accuracy: 0.001)
    }

    // MARK: - Analytics Names

    func test_analyticsName_welcome() {
        XCTAssertEqual(OnboardingStep.welcome.analyticsName, "welcome")
    }

    func test_analyticsName_painPoints() {
        XCTAssertEqual(OnboardingStep.painPoints.analyticsName, "pain_points")
    }
}
