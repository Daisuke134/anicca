import Foundation

/// Compiled into both targets. Individual save/history keys avoid cross-process
/// read-modify-write of a shared array when several widgets are installed.
struct WidgetWord: Codable, Equatable {
    let id: String
    let text: String
    let category: String
}

struct WidgetContentStore {
    let defaults: UserDefaults

    var words: [WidgetWord] {
        guard let data = defaults.data(forKey: "widget_words") else { return [] }
        return (try? JSONDecoder().decode([WidgetWord].self, from: data)) ?? []
    }

    func sync(_ words: [WidgetWord]) {
        guard let data = try? JSONEncoder().encode(words) else { return }
        defaults.set(data, forKey: "widget_words")
    }

    func isSaved(_ id: String) -> Bool {
        defaults.data(forKey: "widget_saved_" + id) != nil
    }

    func save(_ word: WidgetWord) {
        guard words.contains(word), let data = try? JSONEncoder().encode(word) else { return }
        defaults.set(data, forKey: "widget_saved_" + word.id)
    }

    var savedWords: [WidgetWord] {
        defaults.dictionaryRepresentation().keys.filter { $0.hasPrefix("widget_saved_") }.compactMap {
            defaults.data(forKey: $0).flatMap { try? JSONDecoder().decode(WidgetWord.self, from: $0) }
        }
    }

    /// Recent words cool down for a day; positive reactions rank the remaining
    /// personally relevant words. Stable IDs break ties, never the calendar.
    func select(category: String?, now: Date) -> WidgetWord? {
        let candidates = words.filter { category == nil || $0.category == category }
        let likedCategories = Set(savedWords.map(\.category))
        func score(_ word: WidgetWord) -> Int {
            let last = defaults.object(forKey: "widget_presented_" + word.id) as? Date
            let recent = last.map { now.timeIntervalSince($0) < 86400 } ?? false
            return (recent ? -4 : 0) + (isSaved(word.id) ? 2 : 0) + (likedCategories.contains(word.category) ? 1 : 0)
        }
        return candidates.sorted {
            let left = score($0), right = score($1)
            if left != right { return left > right }
            let l = defaults.object(forKey: "widget_presented_" + $0.id) as? Date ?? .distantPast
            let r = defaults.object(forKey: "widget_presented_" + $1.id) as? Date ?? .distantPast
            return l == r ? $0.id < $1.id : l < r
        }.first
    }

    func recordPresentation(_ word: WidgetWord, at date: Date) {
        defaults.set(date, forKey: "widget_presented_" + word.id)
    }

    func hasPremium(at date: Date) -> Bool {
        guard defaults.bool(forKey: "widget_premium") else { return false }
        guard let expiry = defaults.object(forKey: "widget_premium_until") as? Date else { return true }
        return expiry > date
    }

    func clear() {
        for key in defaults.dictionaryRepresentation().keys where key.hasPrefix("widget_") {
            defaults.removeObject(forKey: key)
        }
    }
}
