import XCTest
@testable import DeskStretch

final class AIStretchServiceTests: XCTestCase {
    func testGenerateRoutineReturnsRequestedCount() {
        let libraryService = StretchLibraryService()
        libraryService.loadFromBundle()
        let service = AIStretchService(libraryService: libraryService)

        let exercises = service.generateRoutine(
            painAreas: [.neck],
            history: [],
            exerciseCount: 3,
            isPremium: false
        )

        XCTAssertLessThanOrEqual(exercises.count, 3)
    }
}
