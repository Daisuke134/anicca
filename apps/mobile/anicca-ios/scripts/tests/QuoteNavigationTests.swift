import Foundation

@main
struct QuoteNavigationTests {
    @MainActor
    static func main() {
        let suite = "anicca.quote-navigation.test.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let catalog = [Quote(id: "q001", text: "I can begin again.")]
        let navigation = QuoteNavigationCoordinator(defaults: defaults)
        navigation.request(quoteID: nil, alertBody: "I am worthy of love, exactly as I am.")
        let restored = QuoteNavigationCoordinator(defaults: defaults)
        guard let result = restored.resolveQuote(in: catalog),
              result.text == "I am worthy of love, exactly as I am." else {
            print("FAIL: body-only cold-start notification must display the tapped words")
            exit(1)
        }
        guard restored.pendingRequest == nil else { exit(2) }
        navigation.request(quoteID: "q001", alertBody: "These are different words from an older catalog.")
        guard navigation.resolveQuote(in: catalog)?.text == "These are different words from an older catalog." else { exit(3) }
        navigation.request(quoteID: "q001", alertBody: nil)
        guard navigation.resolveQuote(in: catalog)?.id == "q001" else { exit(4) }
        print("QuoteNavigationTests: PASS")
    }
}
