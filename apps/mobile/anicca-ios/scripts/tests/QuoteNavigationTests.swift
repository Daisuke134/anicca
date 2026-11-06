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
        navigation.request(quoteID: "q001", alertBody: "I CAN BEGIN AGAIN.")
        guard let casePreserved = navigation.resolveQuote(in: catalog),
              casePreserved.id == "q001",
              casePreserved.text == "I CAN BEGIN AGAIN." else {
            print("FAIL: a case-insensitive catalog match must preserve the tapped notification body")
            exit(6)
        }
        navigation.request(quoteID: "q001", alertBody: "Reminder: I can begin again.")
        guard let decorated = navigation.resolveQuote(in: catalog),
              decorated.id == "q001",
              decorated.text == "Reminder: I can begin again." else {
            print("FAIL: a containing catalog match must preserve the tapped notification body")
            exit(7)
        }
        navigation.request(quoteID: "remote-reused", alertBody: "Notification A")
        let first = navigation.resolveQuote(in: catalog)!
        navigation.request(quoteID: "remote-reused", alertBody: "Notification B")
        let second = navigation.resolveQuote(in: catalog + [first])!
        guard first.id != second.id, second.text == "Notification B" else {
            print("FAIL: reused notification IDs must not reuse an older body")
            exit(5)
        }
        print("QuoteNavigationTests: PASS")
    }
}
