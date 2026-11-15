import Foundation
import WidgetKit

@MainActor
enum WidgetExperience {
    private static var generation = 0
    private static let defaults = UserDefaults.standard
    private static let cohortKey = "widget_prompt_cohort"
    private static let eligibleKey = "widget_prompt_eligible_at"
    private static let shownKey = "widget_prompt_shown"

    static var hasAssignedPrompt: Bool { defaults.string(forKey: cohortKey) != nil }

    /// Called only after a person saves a word on the feed, never on app launch.
    static func guideAfterSave() -> Bool {
        if defaults.string(forKey: cohortKey) == nil {
            defaults.set(Bool.random() ? "guide" : "holdout", forKey: cohortKey)
            defaults.set(Date(), forKey: eligibleKey)
            AnalyticsManager.shared.track(.widgetPromptAssigned, properties: ["cohort": cohort, "trigger": "feed_save"])
        }
        return cohort == "guide" && !defaults.bool(forKey: shownKey)
    }

    static func guideShown() {
        defaults.set(true, forKey: shownKey)
        AnalyticsManager.shared.track(.widgetGuideShown, properties: ["cohort": cohort])
    }

    private static var cohort: String { defaults.string(forKey: cohortKey) ?? "unassigned" }

    static func observeInstallation() {
        let observedGeneration = generation
        WidgetCenter.shared.getCurrentConfigurations { result in
            Task { @MainActor in
                guard observedGeneration == generation else { return }
                switch result {
                case .success(let configurations):
                    let installed = configurations.filter { $0.kind == "AniccaWidget" }
                    let elapsed = (defaults.object(forKey: eligibleKey) as? Date).map {
                        max(0, Int(Date().timeIntervalSince($0) / 86400))
                    } ?? -1
                    // Repeated observations allow day-based retention cohorts. Zero
                    // is emitted only after a successful WidgetKit readback.
                    AnalyticsManager.shared.track(.widgetInstallationObserved, properties: [
                        "installed": !installed.isEmpty, "count": installed.count,
                        "families": installed.map { String(describing: $0.family) },
                        "cohort": cohort, "days_since_eligible": elapsed,
                        "guide_shown": defaults.bool(forKey: shownKey)
                    ])
                case .failure:
                    AnalyticsManager.shared.track(.widgetInstallationUnknown, properties: ["cohort": cohort])
                }
            }
        }
    }

    static func recordTap(_ url: URL) {
        let allowed = ["systemSmall", "systemMedium", "systemLarge", "accessoryRectangular"]
        let family = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems?.first { $0.name == "family" }?.value ?? "unknown"
        AnalyticsManager.shared.track(.widgetOpened, properties: [
            "family": allowed.contains(family) ? family : "unknown", "cohort": cohort
        ])
    }

    static func syncPremium(_ info: SubscriptionInfo) {
        let shared = AppGroup.userDefaults
        let changed = shared.bool(forKey: "widget_premium") != info.isEntitled
            || (shared.object(forKey: "widget_premium_until") as? Date) != info.currentPeriodEnd
        shared.set(info.isEntitled, forKey: "widget_premium")
        if let expiry = info.currentPeriodEnd {
            shared.set(expiry, forKey: "widget_premium_until")
        } else {
            shared.removeObject(forKey: "widget_premium_until")
        }
        if changed { WidgetCenter.shared.reloadTimelines(ofKind: "AniccaWidget") }
    }

    static func clear() {
        generation += 1
        WidgetContentStore(defaults: AppGroup.userDefaults).clear()
        for key in [cohortKey, eligibleKey, shownKey] { defaults.removeObject(forKey: key) }
        WidgetCenter.shared.reloadTimelines(ofKind: "AniccaWidget")
    }
}
