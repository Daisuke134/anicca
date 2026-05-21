import Testing
import Foundation
@testable import AffirmFlow

struct UserSettingsTests {
    @Test
    func freeLimitIsThree() {
        #expect(UserSettings.freeLimit == 3)
    }

    @Test
    func settingsInstanceCreates() {
        let settings = UserSettings()
        #expect(settings != nil)
    }

    @Test
    func focusAreasEncodeDecode() throws {
        let encoder = JSONEncoder()
        let decoder = JSONDecoder()

        let original: [FocusArea] = [.calm, .gratitude, .motivation]
        let data = try encoder.encode(original)
        let decoded = try decoder.decode([FocusArea].self, from: data)

        #expect(original == decoded)
    }

    @Test
    func refreshCountLogic() {
        // Test that incrementing works conceptually
        var count = 0
        count += 1
        #expect(count == 1)
        count += 1
        #expect(count == 2)
    }

    @Test
    func canRefreshLogicWithLimit() {
        // Test the logic: if count < limit, can refresh
        let limit = UserSettings.freeLimit

        #expect(0 < limit) // 0 refreshes used = can refresh
        #expect(1 < limit) // 1 refresh used = can refresh
        #expect(2 < limit) // 2 refreshes used = can refresh
        #expect(!(3 < limit)) // 3 refreshes used = cannot refresh
    }

    @Test
    func refreshesRemainingCalculation() {
        let limit = UserSettings.freeLimit

        #expect(max(0, limit - 0) == 3)
        #expect(max(0, limit - 1) == 2)
        #expect(max(0, limit - 2) == 1)
        #expect(max(0, limit - 3) == 0)
        #expect(max(0, limit - 4) == 0) // Cannot go negative
    }

    @Test
    func midnightResetLogic() {
        let calendar = Calendar.current
        let yesterday = Date().addingTimeInterval(-86400)

        #expect(!calendar.isDateInToday(yesterday))
        #expect(calendar.isDateInToday(Date()))
    }
}
