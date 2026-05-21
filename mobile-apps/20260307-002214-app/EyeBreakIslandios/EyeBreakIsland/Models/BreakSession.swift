import Foundation

struct BreakSession: Codable, Identifiable {
    let id: UUID
    let date: Date
    let breakCount: Int
    let totalMinutes: Int

    init(id: UUID = UUID(), date: Date = Date(), breakCount: Int = 0, totalMinutes: Int = 0) {
        self.id = id
        self.date = date
        self.breakCount = breakCount
        self.totalMinutes = totalMinutes
    }
}
