import Foundation
import Mixpanel

class AnalyticsManager {
    static let shared = AnalyticsManager()

    private init() {}

    func trackSessionStarted(breathingType: BreathingType, durationSec: Int) {
        Mixpanel.mainInstance().track(event: "session_started", properties: [
            "breathing_type": breathingType.rawValue,
            "duration_sec": durationSec
        ])
    }

    func trackSessionCompleted(breathingType: BreathingType, durationSec: Int, feltBetter: Bool) {
        Mixpanel.mainInstance().track(event: "session_completed", properties: [
            "breathing_type": breathingType.rawValue,
            "duration_sec": durationSec,
            "felt_better": feltBetter
        ])
    }

    func trackOnboardingCompleted(painType: String) {
        Mixpanel.mainInstance().track(event: "onboarding_completed", properties: [
            "pain_type": painType
        ])
    }

    func trackPaywallViewed(offeringId: String) {
        Mixpanel.mainInstance().track(event: "paywall_viewed", properties: [
            "offering_id": offeringId
        ])
    }
}
