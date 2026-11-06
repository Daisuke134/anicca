import Foundation

@main
struct LikedQuotesTests {
    @MainActor
    static func main() {
        let suite = "anicca.likes.test.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let quote = Quote(id: "notification:unknown", text: "The words that brought me here.")
        let store = LikedQuotesStore(defaults: defaults)
        guard store.toggle(quote) else { exit(1) }
        let restored = LikedQuotesStore(defaults: defaults)
        guard restored.savedQuotes(in: []).first == quote else {
            print("FAIL: a saved notification must remain readable outside the catalog")
            exit(2)
        }
        restored.toggle(quote)
        guard LikedQuotesStore(defaults: defaults).savedQuotes(in: []).isEmpty else { exit(3) }
        print("LikedQuotesTests: PASS")
    }
}
