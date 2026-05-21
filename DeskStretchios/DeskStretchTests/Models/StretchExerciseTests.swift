import XCTest
@testable import DeskStretch

final class StretchExerciseTests: XCTestCase {
    func testDecodeFromJSON() throws {
        let json = """
        {
            "id": "test_exercise",
            "name": "Test",
            "category": "neck",
            "instructions": "Do the thing.",
            "durationSeconds": 30,
            "sfSymbol": "star",
            "isPremium": false
        }
        """.data(using: .utf8)!

        let exercise = try JSONDecoder().decode(StretchExercise.self, from: json)
        XCTAssertEqual(exercise.id, "test_exercise")
        XCTAssertEqual(exercise.category, .neck)
        XCTAssertEqual(exercise.durationSeconds, 30)
        XCTAssertFalse(exercise.isPremium)
    }
}
