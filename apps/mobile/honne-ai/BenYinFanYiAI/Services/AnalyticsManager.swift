import Foundation
import Mixpanel
import OSLog

/// Shared Mixpanel instrumentation for all Anicca-family apps.
/// Event taxonomy and required properties follow
/// `kpi-churn-event-spec-2026-11-11.md` §3.2 / §3.3 (same ruler as Anicca iOS):
/// every event carries app_id / app_environment / app_version / build /
/// platform / os_version / language / country as super properties.
/// Purchase / trial / churn ground truth is RevenueCat's server-side
/// Mixpanel integration (rc_* events, spec §3.5); client purchase events
/// here are auxiliary records with full attribution properties.
final class AnalyticsManager {
    static let shared = AnalyticsManager()

    /// Bundle ID of this app (spec §3.2: app_id is the bundle identifier).
    static let appID = "app.rork.hon-ne-honyaku-ai"

    private let logger = Logger(subsystem: AnalyticsManager.appID, category: "Analytics")
    private(set) var isConfigured = false
    private var onboardingStartedAt: Date?

    private init() {}

    // MARK: - Configuration

    func configure(token: String) {
        guard !isConfigured, !token.isEmpty else { return }
        Mixpanel.initialize(token: token, trackAutomaticEvents: false)
        let instance = Mixpanel.mainInstance()
        instance.loggingEnabled = false
        instance.registerSuperProperties([
            "app_id": Self.appID,
            "app_environment": Self.appEnvironment,
            "app_version": Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "unknown",
            "build": Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "unknown",
            "platform": "ios",
            "os_version": Self.osVersion,
            "language": Locale.preferredLanguages.first ?? Locale.current.identifier,
            "country": (Locale.current as NSLocale).object(forKey: .countryCode) as? String ?? "unknown",
        ])
        isConfigured = true
        logger.info("Mixpanel initialized")
    }

    /// Mixpanel distinct ID, used to link client events with RevenueCat's
    /// server-side events via the reserved `$mixpanel_distinct_id` attribute.
    var distinctId: String? {
        guard isConfigured else { return nil }
        return Mixpanel.mainInstance().distinctId
    }

    static var appEnvironment: String {
        #if targetEnvironment(simulator)
        return "simulator"
        #else
        return Bundle.main.appStoreReceiptURL?.lastPathComponent == "sandboxReceipt" ? "sandbox" : "production"
        #endif
    }

    private static var osVersion: String {
        let v = ProcessInfo.processInfo.operatingSystemVersion
        return "\(v.majorVersion).\(v.minorVersion).\(v.patchVersion)"
    }

    // MARK: - Core tracking

    func track(_ event: String, properties: [String: MixpanelType] = [:]) {
        guard isConfigured else { return }
        var merged = properties
        merged["event_id"] = UUID().uuidString
        merged["event_timestamp"] = Int(Date().timeIntervalSince1970 * 1_000)
        Mixpanel.mainInstance().track(event: event, properties: merged)
        logger.debug("Tracked event: \(event, privacy: .public)")
    }

    // MARK: - Funnel events (spec §3.3)

    func trackAppOpened() {
        let key = "analytics_has_launched_before"
        let isFirst = !UserDefaults.standard.bool(forKey: key)
        if isFirst { UserDefaults.standard.set(true, forKey: key) }
        track("app_opened", properties: ["first_launch": isFirst])
    }

    func trackOnboardingStarted() {
        if onboardingStartedAt == nil { onboardingStartedAt = Date() }
        track("onboarding_started")
    }

    func trackOnboardingCompleted(durationSec: Int) {
        track("onboarding_completed", properties: ["duration_sec": durationSec])
    }

    /// Convenience for call sites that cannot measure the duration themselves:
    /// uses the timestamp recorded by trackOnboardingStarted().
    func trackOnboardingCompleted() {
        let duration = onboardingStartedAt.map { Int(Date().timeIntervalSince($0)) } ?? 0
        trackOnboardingCompleted(durationSec: duration)
    }

    func trackScreenViewed(screenName: String) {
        track("screen_viewed", properties: ["screen_name": screenName])
    }

    /// - Parameter result: one of "granted" / "denied" / "skipped" (spec §3.3 value domain).
    func trackNotificationPermissionResult(result: String, source: String) {
        track("notification_permission_result", properties: [
            "result": result,
            "source": source,
        ])
    }

    func trackCoreResultViewed(resultType: String) {
        track("core_result_viewed", properties: ["result_type": resultType])
    }

    func trackPaywallShown(paywallId: String, placement: String) {
        track("paywall_shown", properties: [
            "paywall_id": paywallId,
            "placement": placement,
        ])
    }

    func trackPurchaseStarted(productId: String, price: Double, currency: String, period: String, trialEligible: Bool) {
        track("purchase_started", properties: [
            "product_id": productId,
            "price": price,
            "currency": currency,
            "period": period,
            "trial_eligible": trialEligible,
        ])
    }

    func trackPurchaseCancelled(productId: String) {
        track("purchase_cancelled", properties: ["product_id": productId])
    }

    func trackPurchaseFailed(productId: String, errorCode: String) {
        track("purchase_failed", properties: [
            "product_id": productId,
            "error_code": errorCode,
        ])
    }

    /// Auxiliary client-side completion record. The funnel's completion
    /// stage is counted from RevenueCat's rc_* events only (spec §3.5).
    func trackPurchaseCompleted(productId: String) {
        track("purchase_completed", properties: ["product_id": productId])
    }

    func trackTrialStarted(productId: String, trialDays: Int) {
        track("trial_started", properties: [
            "product_id": productId,
            "trial_days": trialDays,
        ])
    }

    func trackSubscriptionManagementOpened() {
        track("subscription_management_opened")
    }
}
