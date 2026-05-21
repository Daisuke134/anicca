import Foundation
import SwiftData

@Model
final class GratitudeEntry {
    var date: Date
    var gratitude1: String
    var gratitude2: String
    var gratitude3: String
    var affirmation: String
    var timestamp: Date

    var dateString: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: date)
    }

    init(date: Date, gratitude1: String, gratitude2: String, gratitude3: String, affirmation: String) {
        self.date = date
        self.gratitude1 = gratitude1
        self.gratitude2 = gratitude2
        self.gratitude3 = gratitude3
        self.affirmation = affirmation
        self.timestamp = Date()
    }
}
