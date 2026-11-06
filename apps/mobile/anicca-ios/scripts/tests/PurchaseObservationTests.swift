import Foundation

@main
struct PurchaseObservationTests {
    static func main() {
        let suite = "anicca.purchase-observation.test.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let ledger = PurchaseObservationLedger(defaults: defaults)
        guard !ledger.record(nil), !ledger.record("  "), ledger.record("transaction-1"),
              !ledger.record("transaction-1"),
              !PurchaseObservationLedger(defaults: defaults).record("transaction-1"),
              ledger.record("transaction-2") else {
            print("FAIL: missing, repeated, or restored observations must not create another purchase")
            exit(1)
        }
        print("PurchaseObservationTests: PASS")
    }
}
