// FreePlanServiceTests.swift
// Soft Paywall: FreePlanService unit tests

import XCTest
import UserNotifications
@testable import aniccaios

@MainActor
final class FreePlanServiceTests: XCTestCase {

    private var sut: FreePlanService!
    private var mockDefaults: UserDefaults!
    private var fixedCalendar: Calendar!

    override func setUp() {
        super.setUp()
        mockDefaults = UserDefaults(suiteName: "FreePlanServiceTests")!
        mockDefaults.removePersistentDomain(forName: "FreePlanServiceTests")
        fixedCalendar = Calendar(identifier: .gregorian)
        fixedCalendar.timeZone = TimeZone(identifier: "Asia/Tokyo")!
    }

    override func tearDown() {
        mockDefaults.removePersistentDomain(forName: "FreePlanServiceTests")
        sut = nil
        super.tearDown()
    }

    // MARK: - Helper

    private func makeService(
        now: Date,
        calendar: Calendar? = nil
    ) -> FreePlanService {
        FreePlanService(
            calendar: calendar ?? fixedCalendar,
            nowProvider: { now },
            notificationCenter: .current(),
            defaults: mockDefaults
        )
    }

    private func makeDate(year: Int = 2026, month: Int = 2, day: Int = 6, hour: Int, minute: Int = 0) -> Date {
        var comps = DateComponents()
        comps.year = year
        comps.month = month
        comps.day = day
        comps.hour = hour
        comps.minute = minute
        comps.timeZone = TimeZone(identifier: "Asia/Tokyo")
        return fixedCalendar.date(from: comps)!
    }

    // MARK: - problemForSlot

    func test_problemForSlot_emptyProblems_returnsNil() {
        sut = makeService(now: makeDate(hour: 7))
        let result = sut.problemForSlot(day: 1, slot: 0, problems: [])
        XCTAssertNil(result)
    }

    func test_problemForSlot_singleProblem_returnsSame() {
        sut = makeService(now: makeDate(hour: 7))
        let result = sut.problemForSlot(day: 1, slot: 0, problems: [.stayingUpLate])
        XCTAssertEqual(result, .stayingUpLate)
    }

    func test_problemForSlot_singleProblem_allSlots_returnsSame() {
        sut = makeService(now: makeDate(hour: 7))
        for slot in 0..<3 {
            let result = sut.problemForSlot(day: 1, slot: slot, problems: [.stayingUpLate])
            XCTAssertEqual(result, .stayingUpLate, "Slot \(slot) should return .stayingUpLate")
        }
    }

    func test_problemForSlot_rotates_correctly() {
        sut = makeService(now: makeDate(hour: 7))
        let problems: [ProblemType] = [.anxiety, .rumination, .procrastination]

        // day=1: index = (1-1+slot) % 3 = slot % 3
        XCTAssertEqual(sut.problemForSlot(day: 1, slot: 0, problems: problems), .anxiety)
        XCTAssertEqual(sut.problemForSlot(day: 1, slot: 1, problems: problems), .rumination)
        XCTAssertEqual(sut.problemForSlot(day: 1, slot: 2, problems: problems), .procrastination)
    }

    func test_problemForSlot_day2_rotates() {
        sut = makeService(now: makeDate(hour: 7))
        let problems: [ProblemType] = [.anxiety, .rumination, .procrastination]

        // day=2: index = (2-1+slot) % 3 = (1+slot) % 3
        XCTAssertEqual(sut.problemForSlot(day: 2, slot: 0, problems: problems), .rumination)
        XCTAssertEqual(sut.problemForSlot(day: 2, slot: 1, problems: problems), .procrastination)
        XCTAssertEqual(sut.problemForSlot(day: 2, slot: 2, problems: problems), .anxiety)
    }

    // MARK: - nextScheduledNudgeTimes

    func test_nextScheduledNudgeTimes_beforeAllSlots_returnsThree() {
        sut = makeService(now: makeDate(hour: 7))
        let times = sut.nextScheduledNudgeTimes()
        XCTAssertEqual(times.count, 3)
    }

    func test_nextScheduledNudgeTimes_afterFirstSlot_returnsTwo() {
        sut = makeService(now: makeDate(hour: 9))
        let times = sut.nextScheduledNudgeTimes()
        XCTAssertEqual(times.count, 2)
    }

    func test_nextScheduledNudgeTimes_afterAllSlots_returnsEmpty() {
        sut = makeService(now: makeDate(hour: 21))
        let times = sut.nextScheduledNudgeTimes()
        XCTAssertEqual(times.count, 0)
    }

    // MARK: - scheduleFreePlanNudges

    func test_scheduleFreePlanNudges_emptyProblems_noSchedule() {
        sut = makeService(now: makeDate(hour: 7))
        // 空配列でクラッシュしないことを検証
        sut.scheduleFreePlanNudges(problems: [])
        // 通知は0件（クラッシュしない）
    }

    func test_scheduleFreePlanNudges_savesLastScheduledDay() {
        sut = makeService(now: makeDate(hour: 7))
        sut.scheduleFreePlanNudges(problems: [.anxiety])
        let saved = mockDefaults.integer(forKey: "freePlanLastScheduledDay")
        XCTAssertGreaterThan(saved, 0)
    }

    func test_scheduleFreePlanNudges_strings_convertsToProblems() {
        sut = makeService(now: makeDate(hour: 7))
        sut.scheduleFreePlanNudges(struggles: ["anxiety", "rumination"])
        let saved = mockDefaults.integer(forKey: "freePlanLastScheduledDay")
        XCTAssertGreaterThan(saved, 0)
    }

    // MARK: - rescheduleIfNeeded

    func test_rescheduleIfNeeded_differentDay_reschedules() {
        sut = makeService(now: makeDate(hour: 7))
        // 前日にスケジュールした設定
        mockDefaults.set(100, forKey: "freePlanLastScheduledDay")

        // 今日のdayOfYear != 100 なら再スケジュール
        sut.rescheduleIfNeeded(problems: [.anxiety])

        let saved = mockDefaults.integer(forKey: "freePlanLastScheduledDay")
        XCTAssertNotEqual(saved, 100)
    }

    func test_rescheduleIfNeeded_sameDay_noOp() {
        let now = makeDate(hour: 7)
        sut = makeService(now: now)
        let currentDay = fixedCalendar.ordinality(of: .day, in: .year, for: now) ?? 1
        mockDefaults.set(currentDay, forKey: "freePlanLastScheduledDay")

        sut.rescheduleIfNeeded(problems: [.anxiety])

        let saved = mockDefaults.integer(forKey: "freePlanLastScheduledDay")
        XCTAssertEqual(saved, currentDay)
    }

    // MARK: - dailyLimit

    func test_dailyLimit_isThree() {
        XCTAssertEqual(FreePlanService.dailyLimit, 3)
    }
}
