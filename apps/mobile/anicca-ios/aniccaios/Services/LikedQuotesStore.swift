import Foundation
import Combine

/// UserDefaults-backed Set<String> of liked quote ids.
/// Used by ♡ button + Saved/Liked screens.
@MainActor
final class LikedQuotesStore: ObservableObject {
    @Published private(set) var likedIds: Set<String>

    private static let storageKey = "anicca.liked.ids"
    private static let quotesKey = "anicca.liked.quotes"
    private let defaults: UserDefaults
    private var persistedQuotes: [String: Quote]

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        let raw = defaults.array(forKey: Self.storageKey) as? [String] ?? []
        self.likedIds = Set(raw)
        self.persistedQuotes = defaults.data(forKey: Self.quotesKey)
            .flatMap { try? JSONDecoder().decode([String: Quote].self, from: $0) } ?? [:]
    }

    func isLiked(_ id: String) -> Bool { likedIds.contains(id) }

    func savedQuotes(in catalog: [Quote]) -> [Quote] {
        likedIds.sorted().compactMap { id in
            persistedQuotes[id] ?? catalog.first(where: { $0.id == id })
        }
    }

    @discardableResult
    func toggle(_ quote: Quote) -> Bool {
        if !likedIds.contains(quote.id) { persistedQuotes[quote.id] = quote }
        return toggle(quote.id)
    }

    /// Toggles like state. Returns `true` when the quote was newly favorited.
    @discardableResult
    func toggle(_ id: String) -> Bool {
        if likedIds.contains(id) {
            likedIds.remove(id)
            persistedQuotes.removeValue(forKey: id)
            persist()
            return false
        } else {
            likedIds.insert(id)
            persist()
            return true
        }
    }

    private func persist() {
        defaults.set(Array(likedIds), forKey: Self.storageKey)
        if let data = try? JSONEncoder().encode(persistedQuotes) {
            defaults.set(data, forKey: Self.quotesKey)
        }
    }
}
