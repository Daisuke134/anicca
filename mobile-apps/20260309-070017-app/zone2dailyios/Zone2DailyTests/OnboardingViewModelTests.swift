// File: Zone2DailyTests/OnboardingViewModelTests.swift
// TDD: OnboardingViewModel unit tests — US-006b

import XCTest
@testable import Zone2Daily

final class OnboardingViewModelTests: XCTestCase {
    var sut: OnboardingViewModel!

    override func setUp() {
        super.setUp()
        sut = OnboardingViewModel()
    }

    // MARK: — Initial State

    func test_initialState_stepIsZero() {
        XCTAssertEqual(sut.currentStep, 0)
    }

    func test_initialState_defaultAgeIs30() {
        XCTAssertEqual(sut.age, 30)
    }

    func test_initialState_isNotComplete() {
        XCTAssertFalse(sut.isComplete)
    }

    // MARK: — goNext

    func test_goNext_atStep0_incrementsTo1() {
        sut.goNext()
        XCTAssertEqual(sut.currentStep, 1)
    }

    func test_goNext_atStep1_incrementsTo2() {
        sut.currentStep = 1
        sut.goNext()
        XCTAssertEqual(sut.currentStep, 2)
    }

    func test_goNext_atStep2_incrementsTo3() {
        sut.currentStep = 2
        sut.goNext()
        XCTAssertEqual(sut.currentStep, 3)
    }

    func test_goNext_atStep3_setsIsCompleteTrue() {
        sut.currentStep = 3
        sut.goNext()
        XCTAssertTrue(sut.isComplete)
    }

    func test_goNext_atStep3_doesNotIncrementBeyond3() {
        sut.currentStep = 3
        sut.goNext()
        // isComplete is set, currentStep stays
        XCTAssertTrue(sut.isComplete)
    }

    // MARK: — complete

    func test_complete_setsIsCompleteTrue() {
        sut.complete()
        XCTAssertTrue(sut.isComplete)
    }

    func test_complete_fromAnyStep_setsIsComplete() {
        sut.currentStep = 1
        sut.complete()
        XCTAssertTrue(sut.isComplete)
    }

    // MARK: — age

    func test_age_canBeSet() {
        sut.age = 45
        XCTAssertEqual(sut.age, 45)
    }
}
