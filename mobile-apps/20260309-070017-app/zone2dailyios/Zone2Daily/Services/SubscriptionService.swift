// File: Services/SubscriptionService.swift
// Implements SubscriptionServiceProtocol via RevenueCat SDK
// Source: RevenueCat iOS Quickstart — https://docs.revenuecat.com/docs/ios
// Rule 20: SDK only — RevenueCatUI forbidden
// Rule 23: No AI API

import Foundation
#if DEBUG
@_spi(Internal) import RevenueCat
#else
import RevenueCat
#endif

@Observable
final class SubscriptionService: SubscriptionServiceProtocol {
    var isPremium: Bool = false
    private var isConfigured = false

    func configure(apiKey: String) {
        guard !apiKey.isEmpty else { return }
        #if DEBUG
        // Source: us-005b-monetization.md — uiPreviewMode enables Simulator StoreKit testing
        // iOS 18.4+/26.x では StoreKit が products を返さない (GitHub #4954)
        // uiPreviewMode で RC dashboard offerings から mock products を生成して回避
        Purchases.logLevel = .debug
        let config = Configuration.builder(withAPIKey: apiKey)
            .with(dangerousSettings: DangerousSettings(uiPreviewMode: true))
            .build()
        Purchases.configure(with: config)
        #else
        // Source: RevenueCat docs — .enforced not yet available in RC 5.x, use .informational
        let config = Configuration.builder(withAPIKey: apiKey)
            .with(entitlementVerificationMode: .informational)
            .build()
        Purchases.configure(with: config)
        Purchases.logLevel = .error
        #endif
        isConfigured = true
        Task { await refreshPremiumStatus() }
    }

    func fetchOfferings() async throws -> [Package] {
        guard isConfigured else { return [] }
        let offerings = try await Purchases.shared.offerings()
        return offerings.current?.availablePackages ?? []
    }

    func purchase(package: Package) async throws -> Bool {
        guard isConfigured else { return false }
        #if DEBUG
        // Source: us-005b-monetization.md — uiPreviewMode purchase handling
        // uiPreviewMode では customerInfo.entitlements が空になるため、
        // cancel(1) と simulated failure(42) のみ re-throw、それ以外は成功扱い
        do {
            _ = try await Purchases.shared.purchase(package: package)
            isPremium = true
            return true
        } catch {
            let errorCode = (error as NSError).code
            if errorCode == 1 || errorCode == 42 { throw error }
            isPremium = true
            return true
        }
        #else
        do {
            let result = try await Purchases.shared.purchase(package: package)
            if !result.userCancelled {
                isPremium = true
            }
            return !result.userCancelled
        } catch let error as ErrorCode {
            // Re-throw cancellation; swallow other errors gracefully in production
            if error == .purchaseCancelledError {
                throw error
            }
            return false
        }
        #endif
    }

    func restorePurchases() async throws {
        guard isConfigured else { return }
        let info = try await Purchases.shared.restorePurchases()
        isPremium = info.entitlements["premium"]?.isActive == true
    }

    private func refreshPremiumStatus() async {
        guard isConfigured else { return }
        let info = try? await Purchases.shared.customerInfo()
        isPremium = info?.entitlements["premium"]?.isActive == true
    }
}
