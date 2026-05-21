import Foundation
import RevenueCat

enum RevenueCatService {
    static func configure() {
        #if DEBUG
        Purchases.logLevel = .debug
        let apiKey = Config.EXPO_PUBLIC_REVENUECAT_TEST_API_KEY
        #else
        let apiKey = Config.EXPO_PUBLIC_REVENUECAT_IOS_API_KEY
        #endif

        guard !apiKey.isEmpty else { return }
        Purchases.configure(withAPIKey: apiKey)
    }
}
