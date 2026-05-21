// File: Zone2DailyTests/UserProfileTests.swift
// TDD: UserProfile HR calculation

import XCTest
@testable import Zone2Daily

final class UserProfileTests: XCTestCase {
    func test_zone2MaxHR_age30_is150() {
        let profile = UserProfile(age: 30)
        XCTAssertEqual(profile.zone2MaxHR, 150)
    }

    func test_zone2MinHR_age30_is140() {
        let profile = UserProfile(age: 30)
        XCTAssertEqual(profile.zone2MinHR, 140)
    }

    func test_defaultWeeklyGoal_is150() {
        let profile = UserProfile(age: 30)
        XCTAssertEqual(profile.weeklyGoalMinutes, 150)
    }

    func test_customWeeklyGoal() {
        let profile = UserProfile(age: 30, weeklyGoalMinutes: 200)
        XCTAssertEqual(profile.weeklyGoalMinutes, 200)
    }
}
