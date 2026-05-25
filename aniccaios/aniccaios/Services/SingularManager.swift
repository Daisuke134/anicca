import Foundation
import UIKit
import OSLog

@MainActor
final class SingularManager {
    static let shared = SingularManager()
    private let logger = Logger(subsystem: "com.anicca.ios", category: "Singular")
    private var isConfigured = false

    private init() {}

    func configure(launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) {
        guard !isConfigured else { return }

        guard let config = SingularConfig(
            apiKey: "aniccaai_e8e6f239",
            andSecret: "6ce48fd492d16cf4e7905759762b96cd"
        ) else {
            logger.error("Singular config creation failed")
            return
        }

        // ATT なし: waitForTrackingAuthorization は設定しない
        // SKAN は SDK 12.0.6+ で自動有効（Singular Dashboard で Managed Mode）
        config.launchOptions = launchOptions
        config.skAdNetworkEnabled = true
        config.enableLogging = true

        Singular.start(config)
        isConfigured = true
        logger.info("Singular SDK initialized (IDFV + SKAN, no ATT)")
    }
}
