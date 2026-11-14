import Foundation

/// Keeps one affirmation for the current local day, including the exact first intervention.
@MainActor
final class DailyAffirmationStore {
    static let shared = DailyAffirmationStore()

    private struct Entry: Codable {
        let quote: Quote
        let language: String
        let selectedAt: Date
    }

    private let defaults: UserDefaults
    private let storageKey = "anicca.daily.affirmation"

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    func seed(_ quote: Quote, language: String, now: Date = Date()) {
        let entry = Entry(quote: quote, language: language, selectedAt: now)
        if let data = try? JSONEncoder().encode(entry) {
            defaults.set(data, forKey: storageKey)
        }
    }

    func todayQuote(
        language: String,
        now: Date = Date(),
        calendar: Calendar = .current,
        select: () -> Quote?
    ) -> Quote? {
        if let data = defaults.data(forKey: storageKey),
           let entry = try? JSONDecoder().decode(Entry.self, from: data),
           entry.language == language,
           calendar.isDate(entry.selectedAt, inSameDayAs: now) {
            return entry.quote
        }
        guard let quote = select() else { return nil }
        seed(quote, language: language, now: now)
        return quote
    }
}
