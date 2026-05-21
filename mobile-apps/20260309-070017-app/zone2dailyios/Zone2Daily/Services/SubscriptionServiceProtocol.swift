// File: Services/SubscriptionServiceProtocol.swift
// Protocol-based DI for testability
// Source: Apple Developer — Protocol-based DI
// https://developer.apple.com/documentation/swift/choosing-between-structures-and-classes

import Foundation
import RevenueCat

protocol SubscriptionServiceProtocol {
    var isPremium: Bool { get }
    func configure(apiKey: String)
    func fetchOfferings() async throws -> [Package]
    func purchase(package: Package) async throws -> Bool
    func restorePurchases() async throws
}
