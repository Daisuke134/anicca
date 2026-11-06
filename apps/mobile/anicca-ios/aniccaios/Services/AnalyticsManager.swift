import Foundation
import Mixpanel
import PostHog
import StoreKit
import OSLog
import RevenueCat

/// アプリ全体のアナリティクスを管理するシングルトン
/// Jake Mor's Tip #1: "Most important metric is App Install → Paywall View"
@MainActor
final class AnalyticsManager {
    static let shared = AnalyticsManager()
    private let logger = Logger(subsystem: "com.anicca.ios", category: "Analytics")
    private let purchaseObservations = PurchaseObservationLedger()
    private let sessionID = UUID().uuidString
    private var postHogConfigured = false

    private var context: [String: MixpanelType] {
        #if targetEnvironment(simulator)
        let environment = "simulator"
        #else
        let environment = Bundle.main.appStoreReceiptURL?.lastPathComponent == "sandboxReceipt" ? "sandbox" : "production"
        #endif
        return ["app_version": AppConfig.appVersion,
                "app_build": Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "unknown",
                "app_environment": environment, "flow_version": "affirmation-first-v1",
                "session_id": sessionID, "language": AppState.shared.effectiveLanguage.rawValue]
    }
    
    private init() {}
    
    // MARK: - Configuration
    
    func configure() {
        let token = AppConfig.mixpanelToken
        // trackAutomaticEvents: false (公式推奨 - クライアントサイドの自動イベントは信頼性が低い)
        Mixpanel.initialize(token: token, trackAutomaticEvents: false)
        
        // イベントpayloadを端末ログへ出力しない。
        Mixpanel.mainInstance().loggingEnabled = false
        
        logger.info("Mixpanel initialized")
    }
    
    /// ユーザーIDを設定（ログイン時に呼び出し）
    func identify(userId: String) {
        Mixpanel.mainInstance().identify(distinctId: userId)
        if postHogConfigured { PostHogSDK.shared.identify(userId) }
        logger.info("Mixpanel identified user: \(userId, privacy: .private(mask: .hash))")
    }
    
    /// ユーザープロファイル情報を設定
    func setUserProperties(_ properties: [String: MixpanelType]) {
        Mixpanel.mainInstance().people.set(properties: properties)
    }
    
    /// 単一のユーザープロパティを設定
    /// - Parameters:
    ///   - key: プロパティキー（例: "acquisition_source", "gender"）
    ///   - value: プロパティ値
    func setUserProperty(_ key: String, value: MixpanelType) {
        Mixpanel.mainInstance().people.set(properties: [key: value])
        logger.debug("Set user property: \(key, privacy: .public)")
    }
    
    /// ログアウト時にリセット
    func reset() {
        Mixpanel.mainInstance().reset()
        if postHogConfigured { PostHogSDK.shared.reset() }
        logger.info("Mixpanel reset")
    }
    
    // MARK: - Event Tracking
    
    /// 汎用イベントトラッキング
    func track(_ event: AnalyticsEvent, properties: [String: MixpanelType]? = nil) {
        var merged = context
        merged.merge(properties ?? [:]) { _, incoming in incoming }
        Mixpanel.mainInstance().track(event: event.rawValue, properties: merged)
        if postHogConfigured {
            PostHogSDK.shared.capture(event.rawValue, properties: merged.mapValues { $0 as Any })
        }
        logger.debug("Tracked event: \(event.rawValue, privacy: .public)")
    }

    func connectPostHog(userID: String) {
        postHogConfigured = true
        identify(userId: userID)
        PostHogSDK.shared.register(context.mapValues { $0 as Any })
    }
    
    /// PostHog event tracking (A/B test layer — runs alongside Mixpanel)
    func trackPostHog(_ eventName: String, properties: [String: Any]? = nil) {
        PostHogSDK.shared.capture(eventName, properties: properties)
        logger.debug("PostHog captured: \(eventName, privacy: .public)")
    }

    // MARK: - Convenience Methods

    /// トライアル開始
    func trackTrialStarted(productId: String) {
        track(.trialStarted, properties: [
            "product_id": productId
        ])
    }
    
    /// 購入完了
    func observePurchase(package: Package, transaction: StoreTransaction?, customerInfo: CustomerInfo) {
        guard purchaseObservations.record(transaction?.transactionIdentifier) else { return }
        if customerInfo.entitlements[AppConfig.revenueCatEntitlementId]?.periodType == .trial {
            trackTrialStarted(productId: package.storeProduct.productIdentifier)
            return
        }
        var properties: [String: MixpanelType] = [
            "product_id": package.storeProduct.productIdentifier,
            "transaction_id": transaction?.transactionIdentifier ?? "",
            "displayed_price": NSDecimalNumber(decimal: package.storeProduct.price).doubleValue,
            "amount_source": "store_product_quote_not_settled_revenue"
        ]
        if let currency = package.storeProduct.currencyCode { properties["currency"] = currency }
        track(.purchaseCompleted, properties: properties)
        // Actual amounts/renewals/refunds are reconciled from RevenueCat and Apple.
        updateSKANConversionValue(3)
    }

    /// ペイウォール表示
    func trackPaywallViewed() {
        track(.paywallShown)
        track(.paywallPlanSelectionViewed)
        updateSKANConversionValue(2)
    }

    /// SKAdNetwork conversion value 更新
    func updateSKANConversionValue(_ value: Int) {
        if #available(iOS 16.1, *) {
            let coarse: SKAdNetwork.CoarseConversionValue = value >= 3 ? .high : value >= 1 ? .medium : .low
            SKAdNetwork.updatePostbackConversionValue(value, coarseValue: coarse) { error in
                if let error { self.logger.error("SKAN update failed: \(error.localizedDescription)") }
            }
        } else if #available(iOS 15.4, *) {
            SKAdNetwork.updatePostbackConversionValue(value) { error in
                if let error { self.logger.error("SKAN update failed: \(error.localizedDescription)") }
            }
        }
        logger.debug("SKAN conversion value updated: \(value)")
    }
    
    /// 音声セッション開始
    func trackSessionStarted(habitType: String, customHabitId: String? = nil) {
        var props: [String: MixpanelType] = ["habit_type": habitType]
        if let customId = customHabitId {
            props["custom_habit_id"] = customId
        }
        track(.sessionStarted, properties: props)
    }
    
    /// 音声セッション完了
    func trackSessionCompleted(habitType: String, durationSeconds: Int) {
        track(.sessionCompleted, properties: [
            "habit_type": habitType,
            "duration_seconds": durationSeconds
        ])
    }
}

// MARK: - Analytics Events

enum AnalyticsEvent: String {
    case screenViewed = "screen_viewed"
    case firstAffirmationViewed = "first_affirmation_viewed"
    case affirmationViewed = "affirmation_viewed"
    case affirmationLiked = "affirmation_liked"
    case affirmationUnliked = "affirmation_unliked"
    case affirmationShared = "affirmation_shared"
    case notificationOpened = "notification_opened"
    case notificationDestinationResolved = "notification_destination_resolved"
    case notificationPermissionResult = "notification_permission_result"
    case purchaseCancelled = "purchase_cancelled"
    // App
    case appOpened = "app_opened"

    // Onboarding funnel (v3 — spec-185 Bible-compliant 20-step)
    case onboardingStarted = "onboarding_started"
    case onboardingWelcomeCompleted = "onboarding_welcome_completed"
    case onboardingStrugglesCompleted = "onboarding_struggles_completed"
    case onboardingStruggleDepthCompleted = "onboarding_struggle_depth_completed"
    case onboardingGoalsCompleted = "onboarding_goals_completed"
    case onboardingInsightCompleted = "onboarding_insight_completed"
    case onboardingValuePropCompleted = "onboarding_valueprop_completed"
    case onboardingNotificationsCompleted = "onboarding_notifications_completed"
    case onboardingCompleted = "onboarding_completed"
    case onboardingStepAdvanced = "onboarding_step_advanced"
    case onboardingStepBack = "onboarding_step_back"
    case tinderPainCardAgreed = "tinder_pain_card_agreed"
    case tinderPainCardDismissed = "tinder_pain_card_dismissed"
    case shareCompleted = "share_completed"
    case ratingPromptShown = "rating_prompt_shown"
    case ratingPromptYesTapped = "rating_prompt_yes_tapped"
    case ratingPromptNoTapped = "rating_prompt_no_tapped"
    case ratingStoreReviewRequested = "rating_store_review_requested"
    case feedbackFormSubmitted = "feedback_form_submitted"
    case feedbackFormSkipped = "feedback_form_skipped"

    // Paywall funnel
    case paywallShown = "paywall_shown"
    case paywallPrimerViewed = "paywall_primer_viewed"
    case paywallPlanSelectionViewed = "paywall_plan_selection_viewed"
    case onboardingPaywallCustomerInfoResult = "onboarding_paywall_customer_info_result"
    case onboardingPaywallOfferingLoadResult = "onboarding_paywall_offering_load_result"
    case onboardingPaywallPurchased = "onboarding_paywall_purchased"
    case onboardingPaywallDismissedFree = "onboarding_paywall_dismissed_free"

    // Subscription
    case trialStarted = "trial_started"
    case trialCancelled = "trial_cancelled"
    case purchaseCompleted = "purchase_completed"
    case subscriptionRenewed = "subscription_renewed"
    case subscriptionCancelled = "subscription_cancelled"

    // Voice Session
    case sessionStarted = "session_started"
    case sessionCompleted = "session_completed"
    case sessionFailed = "session_failed"

    // Habits
    case habitCreated = "habit_created"
    case habitDeleted = "habit_deleted"
    case habitNotificationTapped = "habit_notification_tapped"

    // Engagement
    case talkTabOpened = "talk_tab_opened"
    case settingsOpened = "settings_opened"

    // Nudge
    case nudgeTapped = "nudge_tapped"
    case nudgeIgnored = "nudge_ignored"
    case nudgePositiveFeedback = "nudge_positive_feedback"
    case nudgeNegativeFeedback = "nudge_negative_feedback"
    case nudgeScheduled = "nudge_scheduled"
}
