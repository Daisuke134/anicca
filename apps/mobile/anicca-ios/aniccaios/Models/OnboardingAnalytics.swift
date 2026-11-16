import Foundation

/// Pure payload construction for the onboarding funnel (2026-11-15 fix).
///
/// Why this exists: `onboarding_step_completed` used to carry only
/// `step_id` / `step_index`, and step views saved their answers only into
/// the on-device `PersonalizationProfile`. Mixpanel therefore could not
/// break the funnel down by *what the person answered*, so a step could
/// not be improved from data — the defect the owner kept pointing at.
///
/// The single source for the analytics-safe answer vocabulary is
/// `PersonalizationProfile.answerSnapshot()`: it already enumerates every
/// axis, replaces a birth date with the kind token `date_provided`
/// (never the date itself), and replaces the free-text name with
/// `provided` / `unknown` (the name is device-only and is never sent).
/// This file only maps a step to its snapshot axis — it invents no new
/// vocabulary and reads no raw answer storage.
enum OnboardingAnalytics {

    /// Snapshot axis that holds the answer for a step, when the step has
    /// an answer at all. `nil` for the value-moment screens (welcome /
    /// plan reveal), whose completion is still tracked with an empty
    /// `answer_ids` so the funnel stays uniform.
    static func answerAxis(for step: OnboardingStep) -> String? {
        switch step {
        case .welcome, .processing, .planReveal, .comparison:
            return nil
        case .focusCategories: return "focus_categories"
        case .microPreview: return "micro_preview_reaction"
        case .themeChoice: return "theme"
        case .iconChoice: return "app_icon"
        case .widgetPreview: return "widget_interest"
        case .paywall: return nil
        case .goal: return "desired_state"
        case .name: return "name_status"
        case .birthContext: return "birth_context"
        case .moodBaseline: return "mood_baseline"
        case .beliefThemes: return "belief_themes"
        case .tone: return "tone"
        case .lifeContext: return "life_context"
        case .routineAnchors: return "routine_anchors"
        case .priorAttempts: return "prior_attempts"
        case .startReason: return "start_reason"
        case .quietHours: return "quiet_hours"
        case .stressTrigger: return "stress_trigger"
        case .anxietyTarget: return "anxiety_target"
        case .selfCriticism: return "self_criticism"
        case .avoidanceTask: return "avoidance_task"
        case .sleepReason: return "sleep_reason"
        case .bedtime: return "bedtime"
        case .wakeTime: return "wake_time"
        case .priorHelpfulness: return "prior_helpfulness"
        case .painPoints: return "pain_points"
        case .struggleFreq: return "struggle_frequency"
        case .nudgeTimes: return "reminder_slots"
        case .notifications: return "notification_permission"
        }
    }

    /// The selected choice IDs for the step the user just completed.
    ///
    /// Privacy contract (asserted by tests):
    /// - `birthContext` returns zodiac IDs or `["date_provided"]` —
    ///   never a birth date.
    /// - `name` returns `["provided"]` / `["unknown"]` — never the name.
    static func answerIDs(for step: OnboardingStep, profile: PersonalizationProfile) -> [String] {
        guard let axis = answerAxis(for: step) else { return [] }
        return profile.answerSnapshot().values[axis] ?? []
    }

    /// Mixpanel user-property key under which a step's answer is stored,
    /// e.g. `onboarding_answer_mood_baseline`. One key per step so a
    /// person's latest answer per question is queryable as a profile
    /// property, not only inside the completion event.
    static func userPropertyKey(for step: OnboardingStep) -> String {
        "onboarding_answer_\(step.analyticsName)"
    }

    /// User properties to set when a step completes: the step's own
    /// answer (when it has one) as an ID array.
    static func userProperties(for step: OnboardingStep, profile: PersonalizationProfile) -> [(key: String, answerIDs: [String])] {
        guard answerAxis(for: step) != nil else { return [] }
        return [(key: userPropertyKey(for: step), answerIDs: answerIDs(for: step, profile: profile))]
    }

    /// The full `onboarding_step_completed` payload, kept as a value
    /// type so tests can assert the exact shape without Mixpanel.
    struct StepCompletedPayload: Equatable {
        let stepID: String
        let stepIndex: Int
        let flowID: String
        let answerIDs: [String]
        /// Snapshot axis the answer came from, or "" for answer-less steps.
        let answerAxis: String
    }

    static func stepCompletedPayload(step: OnboardingStep, screenID: String, flowID: String, profile: PersonalizationProfile) -> StepCompletedPayload {
        StepCompletedPayload(
            stepID: screenID,
            stepIndex: step.rawValue,
            flowID: flowID,
            answerIDs: answerIDs(for: step, profile: profile),
            answerAxis: answerAxis(for: step) ?? ""
        )
    }
}

/// Dedup state for `onboarding_step_abandoned`.
///
/// Backgrounding used to only *suspend* the current screen visit, so an
/// exit was never recorded and the step a person left at could not be
/// determined. This tracker makes the abandon event fire exactly once
/// per step visit: entering a different step arms it again, completing
/// the pending step disarms it, and re-entering the same step (resume
/// after a backgrounding that already reported) does not re-arm it.
struct OnboardingAbandonmentTracker: Equatable {
    struct PendingStep: Equatable {
        let stepID: String
        let stepIndex: Int
        let flowID: String
    }

    struct AbandonPayload: Equatable {
        let stepID: String
        let stepIndex: Int
        let flowID: String
    }

    private(set) var pending: PendingStep?
    private(set) var hasReportedForPendingStep = false

    /// A step became visible. A different step arms a fresh report;
    /// the same step keeps the already-reported flag.
    mutating func beginStep(stepID: String, stepIndex: Int, flowID: String) {
        let next = PendingStep(stepID: stepID, stepIndex: stepIndex, flowID: flowID)
        if pending != next {
            pending = next
            hasReportedForPendingStep = false
        }
    }

    /// The pending step was completed, so leaving now is not abandonment
    /// of that step. The next step's `beginStep` arms the tracker again.
    mutating func markCompleted() {
        pending = nil
        hasReportedForPendingStep = false
    }

    /// Onboarding finished (questions completed / free completion):
    /// no step can be abandoned afterwards.
    mutating func markOnboardingFinished() {
        markCompleted()
    }

    /// Returns the payload to send, exactly once per armed step.
    /// Subsequent calls return `nil` until a different step is begun.
    mutating func abandonmentPayloadIfNeeded() -> AbandonPayload? {
        guard let pending, !hasReportedForPendingStep else { return nil }
        hasReportedForPendingStep = true
        return AbandonPayload(stepID: pending.stepID, stepIndex: pending.stepIndex, flowID: pending.flowID)
    }
}
