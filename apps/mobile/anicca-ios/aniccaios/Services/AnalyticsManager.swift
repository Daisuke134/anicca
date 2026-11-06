import Foundation
import SwiftUI
import Mixpanel
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
    private var currentScreen: ScreenVisit?

    private struct ScreenVisit {
        let screenID: String
        let screenInstanceID: String
        let flowID: String
        let enteredAt: Date
    }

    private var context: [String: MixpanelType] {
        #if targetEnvironment(simulator)
        let environment = "simulator"
        #else
        let environment = Bundle.main.appStoreReceiptURL?.lastPathComponent == "sandboxReceipt" ? "sandbox" : "production"
        #endif
        var values: [String: MixpanelType] = [
            "app_id": "ai.anicca.app.ios",
            "app_version": AppConfig.appVersion,
            "app_build": Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "unknown",
            "app_environment": environment,
            "flow_version": "affirmation-first-v1",
            "session_id": sessionID,
            "language": AppState.shared.effectiveLanguage.rawValue,
            "locale": Locale.current.identifier,
            "device_region_code": Locale.current.region?.identifier ?? "unknown",
            "storefront_country_code": AppState.shared.currentStorefrontCountryCode ?? "unknown",
        ]
        return values
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
        logger.info("Mixpanel reset")
    }
    
    // MARK: - Event Tracking
    
    /// 汎用イベントトラッキング
    func track(_ event: AnalyticsEvent, properties: [String: MixpanelType]? = nil) {
        var merged = properties ?? [:]
        merged.merge(context) { _, contextValue in contextValue }
        merged["event_id"] = UUID().uuidString
        merged["event_timestamp"] = Int(Date().timeIntervalSince1970 * 1_000)
        Mixpanel.mainInstance().track(event: event.rawValue, properties: merged)
        logger.debug("Tracked event: \(event.rawValue, privacy: .public)")
    }

    func trackScreenViewed(screenID: AnalyticsScreenID, flowID: String, screenInstanceID: String = UUID().uuidString) {
        guard currentScreen?.screenInstanceID != screenInstanceID else { return }
        trackScreenExited(nextScreenID: screenID.rawValue)

        let enteredAt = Date()
        currentScreen = ScreenVisit(
            screenID: screenID.rawValue,
            screenInstanceID: screenInstanceID,
            flowID: flowID,
            enteredAt: enteredAt
        )
        let properties: [String: MixpanelType] = [
            "screen_id": screenID.rawValue,
            "screen_instance_id": screenInstanceID,
            "flow_id": flowID,
            "flow_version": "affirmation-first-v1",
        ]
        track(.screenViewed, properties: properties)
        if screenID == .paywall {
            track(.paywallShown, properties: properties)
            updateSKANConversionValue(2)
        }
    }

    func trackScreenViewedIfNeeded(screenID: AnalyticsScreenID, flowID: String) {
        guard currentScreen?.screenID != screenID.rawValue || currentScreen?.flowID != flowID else { return }
        trackScreenViewed(screenID: screenID, flowID: flowID)
    }

    func trackScreenExited(nextScreenID: String, screenInstanceID: String? = nil) {
        guard let screen = currentScreen else { return }
        guard screenInstanceID == nil || screen.screenInstanceID == screenInstanceID else { return }
        let duration = max(0, Int(Date().timeIntervalSince(screen.enteredAt) * 1_000))
        track(.screenExited, properties: [
            "screen_id": screen.screenID,
            "screen_instance_id": screen.screenInstanceID,
            "flow_id": screen.flowID,
            "next_screen_id": nextScreenID,
            "observed_duration_ms": duration,
        ])
        currentScreen = nil
    }

    /// Backgrounding is not a user exit, so leave it out of screen drop-off events.
    func clearCurrentScreenVisit() {
        currentScreen = nil
    }

    // MARK: - Convenience Methods

    /// トライアル開始
    func trackTrialStarted(productId: String) {
        track(.trialStarted, properties: [
            "product_id": productId
        ])
    }

    func trackPurchaseStarted(productID: String) {
        track(.purchaseStarted, properties: ["product_id": productID])
    }

    func trackPurchaseResult(_ result: String, productID: String, errorCode: String? = nil) {
        var properties: [String: MixpanelType] = [
            "product_id": productID,
            "result": result,
        ]
        if let errorCode { properties["error_code"] = errorCode }
        track(.purchaseResult, properties: properties)
    }

    func trackRestoreStarted(source: String) {
        track(.restoreStarted, properties: ["source": source])
    }

    func trackRestoreResult(_ result: String, source: String, errorCode: String? = nil) {
        var properties: [String: MixpanelType] = ["result": result]
        properties["source"] = source
        if let errorCode { properties["error_code"] = errorCode }
        track(.restoreResult, properties: properties)
    }
    
    /// 購入完了
    func observePurchase(package: Package, transaction: StoreTransaction?, customerInfo: CustomerInfo) {
        guard purchaseObservations.record(transaction?.transactionIdentifier) else { return }
        let entitlement = customerInfo.entitlements[AppConfig.revenueCatEntitlementId]
        let isTrial = entitlement?.isActive == true && entitlement?.periodType == .trial
        var properties: [String: MixpanelType] = [
            "product_id": package.storeProduct.productIdentifier,
            "result": "success",
            "entitlement_state": isTrial ? "trial" : (entitlement?.isActive == true ? "active" : "unknown"),
        ]
        if let currency = package.storeProduct.currencyCode { properties["currency"] = currency }

        track(.purchaseResult, properties: properties)
        if isTrial { trackTrialStarted(productId: package.storeProduct.productIdentifier) }
        // Actual amounts/renewals/refunds are reconciled from RevenueCat and Apple.
        updateSKANConversionValue(3)
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
    case screenExited = "screen_exited"
    case firstAffirmationViewed = "first_affirmation_viewed"
    case affirmationViewed = "affirmation_viewed"
    case affirmationLiked = "affirmation_liked"
    case affirmationUnliked = "affirmation_unliked"
    case affirmationShared = "affirmation_shared"
    case notificationOpened = "notification_opened"
    case notificationReceived = "notification_received"
    case notificationRegistrationResult = "notification_registration_result"
    case notificationDestinationResolved = "notification_destination_resolved"
    case notificationPermissionRequested = "notification_permission_requested"
    case notificationPermissionResult = "notification_permission_result"
    case purchaseStarted = "purchase_started"
    case purchaseResult = "purchase_result"
    case restoreStarted = "restore_started"
    case restoreResult = "restore_result"
    case experimentExposure = "experiment_exposure"
    case productSelected = "product_selected"
    // App
    case appOpened = "app_opened"

    // Onboarding funnel (v3 — spec-185 Bible-compliant 20-step)
    case onboardingStarted = "onboarding_started"
    case onboardingStepCompleted = "onboarding_step_completed"
    case onboardingStepViewed = "onboarding_step_viewed"
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

enum AnalyticsScreenID: String, CaseIterable {
    case onboardingWelcome = "onboarding.welcome"
    case onboardingGoal = "onboarding.goal"
    case onboardingPainPoints = "onboarding.pain_points"
    case onboardingStruggleFrequency = "onboarding.struggle_frequency"
    case onboardingReminderSchedule = "onboarding.reminder_schedule"
    case onboardingProcessing = "onboarding.processing"
    case onboardingFirstAffirmation = "onboarding.first_affirmation"
    case onboardingComparison = "onboarding.comparison"
    case onboardingNotifications = "onboarding.notifications"
    case paywall = "paywall"
    case retentionOffer = "paywall.retention_offer"
    case feed = "feed"
    case feedCollections = "feed.collections"
    case feedSaved = "feed.saved"
    case feedReminders = "feed.reminders"
    case feedThemes = "feed.themes"
    case feedSettings = "feed.settings"
    case settingsSubscription = "settings.subscription"

    static func onboarding(_ step: OnboardingStep) -> AnalyticsScreenID {
        switch step {
        case .welcome: return .onboardingWelcome
        case .goal: return .onboardingGoal
        case .painPoints: return .onboardingPainPoints
        case .struggleFreq: return .onboardingStruggleFrequency
        case .nudgeTimes: return .onboardingReminderSchedule
        case .processing: return .onboardingProcessing
        case .planReveal: return .onboardingFirstAffirmation
        case .comparison: return .onboardingComparison
        case .notifications: return .onboardingNotifications
        }
    }
}

private struct AnalyticsScreenModifier: ViewModifier {
    let screenID: AnalyticsScreenID
    let flowID: String
    @State private var screenInstanceID = UUID().uuidString

    func body(content: Content) -> some View {
        content.onAppear {
            screenInstanceID = UUID().uuidString
            AnalyticsManager.shared.trackScreenViewed(
                screenID: screenID,
                flowID: flowID,
                screenInstanceID: screenInstanceID
            )
        }
    }
}

extension View {
    func analyticsScreen(_ screenID: AnalyticsScreenID, flowID: String) -> some View {
        modifier(AnalyticsScreenModifier(screenID: screenID, flowID: flowID))
    }
}
