// OnboardingAnalyticsTests.swift
// Tests for the 2026-11-15 Mixpanel onboarding fix: step-completed events
// must carry the step's answer_ids, answers must also be settable as user
// properties, birth dates / names must never leak, and the abandonment
// tracker must fire exactly once per step visit.

import XCTest
@testable import aniccaios

final class OnboardingAnalyticsTests: XCTestCase {

    private func profileWithAdaptive(_ configure: (inout AdaptiveAnswers) -> Void) -> PersonalizationProfile {
        var profile = PersonalizationProfile()
        var answers = AdaptiveAnswers()
        configure(&answers)
        profile.adaptiveAnswers = answers
        return profile
    }

    // MARK: - answer_ids per step type

    func test_answerIDs_adaptiveSingleChoice() {
        let profile = profileWithAdaptive { $0.set(.moodBaseline, ids: ["heavy"]) }
        XCTAssertEqual(OnboardingAnalytics.answerIDs(for: .moodBaseline, profile: profile), ["heavy"])
    }

    func test_answerIDs_adaptiveMultipleChoice() {
        let profile = profileWithAdaptive { $0.set(.beliefThemes, ids: ["courage", "gratitude"]) }
        XCTAssertEqual(OnboardingAnalytics.answerIDs(for: .beliefThemes, profile: profile), ["courage", "gratitude"])
    }

    func test_answerIDs_strugglesStep_usesPainPoints() {
        var profile = PersonalizationProfile()
        profile.painPointIds = ["stress", "sleep"]
        XCTAssertEqual(OnboardingAnalytics.answerIDs(for: .painPoints, profile: profile), ["stress", "sleep"])
    }

    func test_answerIDs_struggleDepthStep_usesFrequency() {
        var profile = PersonalizationProfile()
        profile.struggleFrequency = "daily"
        XCTAssertEqual(OnboardingAnalytics.answerIDs(for: .struggleFreq, profile: profile), ["daily"])
    }

    func test_answerIDs_goalStep_usesDesiredState() {
        var profile = PersonalizationProfile()
        profile.desiredState = "calm"
        XCTAssertEqual(OnboardingAnalytics.answerIDs(for: .goal, profile: profile), ["calm"])
    }

    func test_answerIDs_reminderStep_usesSlotTokens() {
        var profile = PersonalizationProfile()
        profile.nudgeSlots = [NudgeSlot(hour: 8, minute: 0), NudgeSlot(hour: 12, minute: 30)]
        profile.dailyFrequency = 2
        XCTAssertEqual(OnboardingAnalytics.answerIDs(for: .nudgeTimes, profile: profile), ["slot_8_0", "slot_12_30"])
    }

    func test_answerIDs_notificationStep_usesPermissionResult() {
        let profile = profileWithAdaptive { $0.set(.moodBaseline, ids: ["neutral"]) }
        var withPermission = profile
        withPermission.recordNotificationPermission("allowed")
        XCTAssertEqual(OnboardingAnalytics.answerIDs(for: .notifications, profile: withPermission), ["allowed"])
    }

    func test_answerIDs_answerlessSteps_areEmpty() {
        let profile = PersonalizationProfile()
        XCTAssertEqual(OnboardingAnalytics.answerIDs(for: .welcome, profile: profile), [])
        XCTAssertEqual(OnboardingAnalytics.answerIDs(for: .planReveal, profile: profile), [])
    }

    func test_answerIDs_unansweredAdaptiveStep_isUnknownNotMissing() {
        let profile = PersonalizationProfile()
        XCTAssertEqual(OnboardingAnalytics.answerIDs(for: .moodBaseline, profile: profile), ["unknown"])
    }

    // MARK: - Privacy: birth date and name never leave the device

    func test_answerIDs_birthContextWithDate_isKindTokenOnly() {
        let profile = profileWithAdaptive {
            $0.setBirthContext(birthDate: Date(timeIntervalSince1970: 0), zodiacIDs: [])
        }
        let ids = OnboardingAnalytics.answerIDs(for: .birthContext, profile: profile)
        XCTAssertEqual(ids, ["date_provided"])
    }

    func test_answerIDs_birthContextWithZodiac_isZodiacOnly() {
        let profile = profileWithAdaptive {
            $0.setBirthContext(birthDate: nil, zodiacIDs: ["leo"])
        }
        XCTAssertEqual(OnboardingAnalytics.answerIDs(for: .birthContext, profile: profile), ["leo"])
    }

    func test_answerIDs_nameStep_isStatusOnlyNeverTheName() {
        var profile = PersonalizationProfile()
        profile.preferredName = "SecretName"
        let ids = OnboardingAnalytics.answerIDs(for: .name, profile: profile)
        XCTAssertEqual(ids, ["provided"])
        XCTAssertFalse(ids.contains("SecretName"))

        let anonymous = PersonalizationProfile()
        XCTAssertEqual(OnboardingAnalytics.answerIDs(for: .name, profile: anonymous), ["unknown"])
    }

    // MARK: - Completed payload shape (the example asserted in the fix report)

    func test_stepCompletedPayload_carriesAnswerIDs() {
        let profile = profileWithAdaptive { $0.set(.moodBaseline, ids: ["heavy"]) }
        let payload = OnboardingAnalytics.stepCompletedPayload(
            step: .moodBaseline, screenID: "onboarding.mood_baseline", flowID: "onboarding", profile: profile)
        XCTAssertEqual(payload.stepID, "onboarding.mood_baseline")
        XCTAssertEqual(payload.stepIndex, OnboardingStep.moodBaseline.rawValue)
        XCTAssertEqual(payload.flowID, "onboarding")
        XCTAssertEqual(payload.answerIDs, ["heavy"])
        XCTAssertEqual(payload.answerAxis, "mood_baseline")
    }

    func test_userProperties_usePerStepKeyAndSameIDs() {
        let profile = profileWithAdaptive { $0.set(.tone, ids: ["gentle"]) }
        let properties = OnboardingAnalytics.userProperties(for: .tone, profile: profile)
        XCTAssertEqual(properties.count, 1)
        XCTAssertEqual(properties.first?.key, "onboarding_answer_tone")
        XCTAssertEqual(properties.first?.answerIDs, ["gentle"])
        XCTAssertEqual(OnboardingAnalytics.userProperties(for: .welcome, profile: profile).count, 0)
    }

    // MARK: - Analytics event name

    func test_analytics_onboardingStepAbandoned_exists() {
        XCTAssertEqual(AnalyticsEvent.onboardingStepAbandoned.rawValue, "onboarding_step_abandoned")
    }

    // MARK: - Abandonment tracker: exactly once per step visit

    func test_abandonment_firesOnceForPendingStep() {
        var tracker = OnboardingAbandonmentTracker()
        tracker.beginStep(stepID: "onboarding.mood_baseline", stepIndex: 11, flowID: "onboarding")
        let first = tracker.abandonmentPayloadIfNeeded()
        XCTAssertEqual(first?.stepID, "onboarding.mood_baseline")
        XCTAssertEqual(first?.stepIndex, 11)
        XCTAssertEqual(first?.flowID, "onboarding")
        XCTAssertNil(tracker.abandonmentPayloadIfNeeded())
    }

    func test_abandonment_sameStepReentry_doesNotRearm() {
        var tracker = OnboardingAbandonmentTracker()
        tracker.beginStep(stepID: "onboarding.tone", stepIndex: 13, flowID: "onboarding")
        XCTAssertNotNil(tracker.abandonmentPayloadIfNeeded())
        tracker.beginStep(stepID: "onboarding.tone", stepIndex: 13, flowID: "onboarding")
        XCTAssertNil(tracker.abandonmentPayloadIfNeeded())
    }

    func test_abandonment_newStep_rearms() {
        var tracker = OnboardingAbandonmentTracker()
        tracker.beginStep(stepID: "onboarding.tone", stepIndex: 13, flowID: "onboarding")
        XCTAssertNotNil(tracker.abandonmentPayloadIfNeeded())
        tracker.beginStep(stepID: "onboarding.life_context", stepIndex: 14, flowID: "onboarding")
        let payload = tracker.abandonmentPayloadIfNeeded()
        XCTAssertEqual(payload?.stepID, "onboarding.life_context")
        XCTAssertNil(tracker.abandonmentPayloadIfNeeded())
    }

    func test_abandonment_completedStep_doesNotFire() {
        var tracker = OnboardingAbandonmentTracker()
        tracker.beginStep(stepID: "onboarding.tone", stepIndex: 13, flowID: "onboarding")
        tracker.markCompleted()
        XCTAssertNil(tracker.abandonmentPayloadIfNeeded())
    }

    func test_abandonment_noPendingStep_doesNotFire() {
        var tracker = OnboardingAbandonmentTracker()
        XCTAssertNil(tracker.abandonmentPayloadIfNeeded())
        tracker.beginStep(stepID: "onboarding.tone", stepIndex: 13, flowID: "onboarding")
        tracker.markOnboardingFinished()
        XCTAssertNil(tracker.abandonmentPayloadIfNeeded())
    }
}
