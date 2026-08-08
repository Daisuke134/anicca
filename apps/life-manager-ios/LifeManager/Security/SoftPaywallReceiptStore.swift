import Foundation

protocol SoftPaywallReceiptStoring: Sendable {
    func hasPresented(for userID: String) async -> Bool
    func markPresented(for userID: String) async
}

actor UserDefaultsSoftPaywallReceiptStore: SoftPaywallReceiptStoring {
    private let defaults: UserDefaults
    private let storageKey: String

    init(
        defaults: UserDefaults = .standard,
        storageKey: String = "ai.anicca.life-manager.soft-paywall.presented-users"
    ) {
        self.defaults = defaults
        self.storageKey = storageKey
    }

    func hasPresented(for userID: String) async -> Bool {
        (defaults.stringArray(forKey: storageKey) ?? []).contains(userID)
    }

    func markPresented(for userID: String) async {
        var presented = Set(defaults.stringArray(forKey: storageKey) ?? [])
        presented.insert(userID)
        defaults.set(Array(presented).sorted(), forKey: storageKey)
    }
}
