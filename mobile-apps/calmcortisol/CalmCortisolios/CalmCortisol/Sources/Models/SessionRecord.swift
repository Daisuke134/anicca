import Foundation

struct SessionRecord: Codable, Identifiable {
    let id: UUID
    let breathingType: String
    let durationSec: Int
    let completedAt: Date
    var feltBetter: Bool?

    init(breathingType: BreathingType, durationSec: Int) {
        self.id = UUID()
        self.breathingType = breathingType.rawValue
        self.durationSec = durationSec
        self.completedAt = Date()
    }
}

class SessionStore {
    static let shared = SessionStore()
    private let key = "session_records"

    private init() {}

    func save(_ record: SessionRecord) {
        var records = loadAll()
        records.append(record)
        if let data = try? JSONEncoder().encode(records) {
            UserDefaults.standard.set(data, forKey: key)
        }
    }

    func loadAll() -> [SessionRecord] {
        guard let data = UserDefaults.standard.data(forKey: key),
              let records = try? JSONDecoder().decode([SessionRecord].self, from: data) else {
            return []
        }
        return records
    }

    func todayCount() -> Int {
        let calendar = Calendar.current
        return loadAll().filter { calendar.isDateInToday($0.completedAt) }.count
    }
}
