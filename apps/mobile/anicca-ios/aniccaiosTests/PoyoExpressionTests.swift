import XCTest
@testable import aniccaios

final class PoyoExpressionTests: XCTestCase {

    // MARK: - Asset mapping

    func test_imageNames_matchAssetCatalogImagesets() {
        XCTAssertEqual(PoyoExpression.happy.imageName, "PoyoHappy")
        XCTAssertEqual(PoyoExpression.sleepy.imageName, "PoyoSleepy")
        XCTAssertEqual(PoyoExpression.sad.imageName, "PoyoSad")
        XCTAssertEqual(PoyoExpression.excited.imageName, "PoyoExcited")
        XCTAssertEqual(PoyoExpression.laughing.imageName, "PoyoLaughing")
    }

    func test_fileNames_matchExportedPNGNames() {
        XCTAssertEqual(PoyoExpression.happy.fileName, "poyo-happy")
        XCTAssertEqual(PoyoExpression.sleepy.fileName, "poyo-sleepy")
        XCTAssertEqual(PoyoExpression.sad.fileName, "poyo-sad")
        XCTAssertEqual(PoyoExpression.excited.fileName, "poyo-excited")
        XCTAssertEqual(PoyoExpression.laughing.fileName, "poyo-laughing")
    }

    // MARK: - Payload parsing (remote wins, spec §3.4)

    func test_payload_parsesAllCases() {
        for expression in PoyoExpression.allCases {
            XCTAssertEqual(PoyoExpression(payloadValue: expression.rawValue), expression)
        }
    }

    func test_payload_isCaseInsensitive() {
        XCTAssertEqual(PoyoExpression(payloadValue: "SLEEPY"), .sleepy)
    }

    func test_payload_rejectsUnknownAndNil() {
        XCTAssertNil(PoyoExpression(payloadValue: "angry"))
        XCTAssertNil(PoyoExpression(payloadValue: ""))
        XCTAssertNil(PoyoExpression(payloadValue: nil))
    }

    // MARK: - §4 mapping: intervention type

    func test_select_bedtimeIsSleepy() {
        XCTAssertEqual(PoyoExpression.select(interventionType: "bedtime", hour: 21, isReturningAfterAbsence: false), .sleepy)
    }

    func test_select_ruminationIsSad() {
        XCTAssertEqual(PoyoExpression.select(interventionType: "rumination", hour: 10, isReturningAfterAbsence: false), .sad)
        XCTAssertEqual(PoyoExpression.select(interventionType: "feeling_self_loathing", hour: 10, isReturningAfterAbsence: false), .sad)
    }

    func test_select_streakIsExcited() {
        XCTAssertEqual(PoyoExpression.select(interventionType: "streak", hour: 9, isReturningAfterAbsence: false), .excited)
        XCTAssertEqual(PoyoExpression.select(interventionType: "challenge", hour: 9, isReturningAfterAbsence: false), .excited)
    }

    func test_select_comedyIsLaughing() {
        XCTAssertEqual(PoyoExpression.select(interventionType: "comedy", hour: 12, isReturningAfterAbsence: false), .laughing)
        XCTAssertEqual(PoyoExpression.select(interventionType: "celebration", hour: 12, isReturningAfterAbsence: false), .laughing)
    }

    func test_select_defaultDaytimeIsHappy() {
        XCTAssertEqual(PoyoExpression.select(interventionType: nil, hour: 10, isReturningAfterAbsence: false), .happy)
        XCTAssertEqual(PoyoExpression.select(interventionType: "wake_up", hour: 7, isReturningAfterAbsence: false), .happy)
        XCTAssertEqual(PoyoExpression.select(interventionType: "unknown_type", hour: 15, isReturningAfterAbsence: false), .happy)
    }

    // MARK: - §4 mapping: time of day boundaries

    func test_select_nightBoundaries() {
        XCTAssertEqual(PoyoExpression.select(interventionType: nil, hour: 22, isReturningAfterAbsence: false), .sleepy)
        XCTAssertEqual(PoyoExpression.select(interventionType: nil, hour: 23, isReturningAfterAbsence: false), .sleepy)
        XCTAssertEqual(PoyoExpression.select(interventionType: nil, hour: 0, isReturningAfterAbsence: false), .sleepy)
        XCTAssertEqual(PoyoExpression.select(interventionType: nil, hour: 4, isReturningAfterAbsence: false), .sleepy)
        XCTAssertEqual(PoyoExpression.select(interventionType: nil, hour: 5, isReturningAfterAbsence: false), .happy)
        XCTAssertEqual(PoyoExpression.select(interventionType: nil, hour: 21, isReturningAfterAbsence: false), .happy)
    }

    // MARK: - No-blame reunion exception (spec §3): wins over everything

    func test_select_returningAfterAbsenceIsAlwaysHappy() {
        XCTAssertEqual(PoyoExpression.select(interventionType: "rumination", hour: 23, isReturningAfterAbsence: true), .happy)
        XCTAssertEqual(PoyoExpression.select(interventionType: "bedtime", hour: 23, isReturningAfterAbsence: true), .happy)
        XCTAssertEqual(PoyoExpression.select(interventionType: nil, hour: 2, isReturningAfterAbsence: true), .happy)
    }

    // MARK: - State mapping

    func test_state_expressions() {
        XCTAssertEqual(PoyoState.idle.expression, .happy)
        XCTAssertEqual(PoyoState.waiting.expression, .sleepy)
        XCTAssertEqual(PoyoState.error.expression, .sad)
        XCTAssertEqual(PoyoState.celebrating.expression, .laughing)
    }

    func test_state_fromExpression() {
        XCTAssertEqual(PoyoState.from(expression: .happy), .idle)
        XCTAssertEqual(PoyoState.from(expression: .sleepy), .waiting)
        XCTAssertEqual(PoyoState.from(expression: .sad), .error)
        XCTAssertEqual(PoyoState.from(expression: .excited), .happy)
        XCTAssertEqual(PoyoState.from(expression: .laughing), .celebrating)
    }

    // MARK: - Presence (absence threshold)

    func test_presence_firstLaunchIsNotReturning() {
        let defaults = UserDefaults(suiteName: "poyo-tests-\(UUID().uuidString)")!
        let now = Date(timeIntervalSince1970: 1_700_000_000)
        XCTAssertFalse(PoyoPresence.isReturningAfterAbsence(now: now, defaults: defaults))
    }

    func test_presence_threeDaysIsReturning_twoDaysIsNot() {
        let defaults = UserDefaults(suiteName: "poyo-tests-\(UUID().uuidString)")!
        let t0 = Date(timeIntervalSince1970: 1_700_000_000)
        PoyoPresence.markSeen(now: t0, defaults: defaults)
        XCTAssertFalse(PoyoPresence.isReturningAfterAbsence(now: t0.addingTimeInterval(2 * 24 * 3600), defaults: defaults))
        XCTAssertTrue(PoyoPresence.isReturningAfterAbsence(now: t0.addingTimeInterval(3 * 24 * 3600), defaults: defaults))
        XCTAssertTrue(PoyoPresence.isReturningAfterAbsence(now: t0.addingTimeInterval(10 * 24 * 3600), defaults: defaults))
    }
}
