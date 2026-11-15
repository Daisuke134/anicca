import Foundation
import Combine
import WidgetKit

/// UserDefaults-backed Set<String> of liked quote ids.
/// Used by ♡ button + Saved/Liked screens.
@MainActor
final class LikedQuotesStore: ObservableObject {
    @Published private(set) var likedIds: Set<String>

    private static let storageKey = "anicca.liked.ids"
    private static let quotesKey = "anicca.liked.quotes"
    private static let themesKey = "anicca.liked.themes"
    private let defaults: UserDefaults
    private var persistedQuotes: [String: Quote]
    private var persistedThemes: [String: String]

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        let raw = defaults.array(forKey: Self.storageKey) as? [String] ?? []
        self.likedIds = Set(raw)
        self.persistedQuotes = defaults.data(forKey: Self.quotesKey)
            .flatMap { try? JSONDecoder().decode([String: Quote].self, from: $0) } ?? [:]
        self.persistedThemes = defaults.dictionary(forKey: Self.themesKey) as? [String: String] ?? [:]
    }

    func importWidgetSaves() {
        let shared = AppGroup.userDefaults
        for word in WidgetContentStore(defaults: shared).savedWords {
            let importedKey = "widget_imported_" + word.id
            guard !shared.bool(forKey: importedKey) else { continue }
            likedIds.insert(word.id)
            persistedQuotes[word.id] = Quote(id: word.id, text: word.text)
            persistedThemes[word.id] = "sageMist"
            persist()
            shared.set(true, forKey: importedKey)
        }
    }

    func isLiked(_ id: String) -> Bool { likedIds.contains(id) }

    /// Favorites saved before theme snapshots were introduced use the original free theme.
    func themeID(for id: String) -> String { persistedThemes[id] ?? "sageMist" }

    func savedQuotes(in catalog: [Quote]) -> [Quote] {
        likedIds.sorted().compactMap { id in
            persistedQuotes[id] ?? catalog.first(where: { $0.id == id })
        }
    }

    @discardableResult
    func toggle(_ quote: Quote, themeID: String? = nil) -> Bool {
        if !likedIds.contains(quote.id) {
            persistedQuotes[quote.id] = quote
            persistedThemes[quote.id] = themeID ?? defaults.string(forKey: "anicca.theme") ?? "sageMist"
        }
        return toggle(quote.id)
    }

    /// Toggles like state. Returns `true` when the quote was newly favorited.
    @discardableResult
    func toggle(_ id: String) -> Bool {
        if likedIds.contains(id) {
            likedIds.remove(id)
            if id.hasPrefix("nudge_") {
                AppGroup.userDefaults.removeObject(forKey: "widget_saved_" + id)
                AppGroup.userDefaults.removeObject(forKey: "widget_imported_" + id)
                WidgetCenter.shared.reloadTimelines(ofKind: "AniccaWidget")
            }
            persistedQuotes.removeValue(forKey: id)
            persistedThemes.removeValue(forKey: id)
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
        defaults.set(persistedThemes, forKey: Self.themesKey)
        if let data = try? JSONEncoder().encode(persistedQuotes) {
            defaults.set(data, forKey: Self.quotesKey)
        }
    }
}
