import XCTest
@testable import FrostDip

final class PlungeProtocolTests: XCTestCase {
    func testInit_setsProperties() {
        let proto = PlungeProtocol(name: "Test", prepTime: 60, coldTime: 120)
        XCTAssertEqual(proto.name, "Test")
        XCTAssertEqual(proto.prepTime, 60)
        XCTAssertEqual(proto.coldTime, 120)
        XCTAssertEqual(proto.hotTime, 0)
        XCTAssertEqual(proto.rounds, 1)
        XCTAssertEqual(proto.restTime, 0)
        XCTAssertFalse(proto.isDefault)
    }

    func testInit_contrastProtocol() {
        let proto = PlungeProtocol(name: "Contrast", prepTime: 60, coldTime: 120, hotTime: 180, rounds: 3, restTime: 30)
        XCTAssertEqual(proto.hotTime, 180)
        XCTAssertEqual(proto.rounds, 3)
        XCTAssertEqual(proto.restTime, 30)
    }

    func testDefaultProtocols_returnsFour() {
        let defaults = PlungeProtocol.defaultProtocols()
        XCTAssertEqual(defaults.count, 4)
        XCTAssertTrue(defaults.allSatisfy { $0.isDefault })
    }

    func testDefaultProtocols_namesCorrect() {
        let defaults = PlungeProtocol.defaultProtocols()
        let names = defaults.map(\.name)
        XCTAssertTrue(names.contains("Beginner"))
        XCTAssertTrue(names.contains("Intermediate"))
        XCTAssertTrue(names.contains("Advanced"))
        XCTAssertTrue(names.contains("Contrast Therapy"))
    }

    func testDefaultProtocols_contrastHasHotTime() {
        let defaults = PlungeProtocol.defaultProtocols()
        let contrast = defaults.first { $0.name == "Contrast Therapy" }!
        XCTAssertGreaterThan(contrast.hotTime, 0)
        XCTAssertGreaterThan(contrast.rounds, 1)
    }
}
