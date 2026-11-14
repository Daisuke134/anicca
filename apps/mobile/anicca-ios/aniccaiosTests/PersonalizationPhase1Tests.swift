import XCTest
@testable import aniccaios

/// Phase 1 personalization: answer→change mapping rules, selector behavior,
/// and the onboarding journey order. These encode the contract of
/// `files/onboarding-answer-change-mapping-2026-11-14.md` (anicca-ops).
final class PersonalizationPhase1Tests: XCTestCase {

    // MARK: - Schedule proposals

    func test_proposedFrequency_followsMapping() {
        XCTAssertEqual(PersonalizationRules.proposedFrequency(struggleFrequency: "rarely"), 1)
        XCTAssertEqual(PersonalizationRules.proposedFrequency(struggleFrequency: "weekly"), 1)
        XCTAssertEqual(PersonalizationRules.proposedFrequency(struggleFrequency: "daily"), 2)
        XCTAssertEqual(PersonalizationRules.proposedFrequency(struggleFrequency: "many_times_daily"), 3)
        XCTAssertEqual(PersonalizationRules.proposedFrequency(struggleFrequency: nil), 1)
    }

    func test_proposedSlots_defaultIsMorningFirst() {
        let slots = PersonalizationRules.proposedSlots(painPointIds: [], frequency: 2)
        XCTAssertEqual(slots, [NudgeSlot(hour: 8, minute: 0), NudgeSlot(hour: 12, minute: 30)])
    }

    func test_proposedSlots_sleepPainShiftsProposalToEvening() {
        let slots = PersonalizationRules.proposedSlots(painPointIds: ["sleep"], frequency: 2)
        XCTAssertEqual(slots, [NudgeSlot(hour: 17, minute: 30), NudgeSlot(hour: 21, minute: 30)])
    }

    func test_scheduleValidation_frequencyMustNotExceedSlots() {
        XCTAssertTrue(PersonalizationRules.isValidSchedule(
            slots: [NudgeSlot(hour: 8, minute: 0), NudgeSlot(hour: 21, minute: 30)], frequency: 2))
        XCTAssertFalse(PersonalizationRules.isValidSchedule(
            slots: [NudgeSlot(hour: 8, minute: 0)], frequency: 2))
        XCTAssertFalse(PersonalizationRules.isValidSchedule(slots: [], frequency: 1))
        XCTAssertFalse(PersonalizationRules.isValidSchedule(
            slots: [NudgeSlot(hour: 8, minute: 0), NudgeSlot(hour: 8, minute: 0)], frequency: 1))
    }

    func test_intensity_followsMapping() {
        XCTAssertEqual(PersonalizationRules.intensity(struggleFrequency: "rarely"), "gentle")
        XCTAssertEqual(PersonalizationRules.intensity(struggleFrequency: "weekly"), "gentle")
        XCTAssertEqual(PersonalizationRules.intensity(struggleFrequency: "daily"), "supportive")
        XCTAssertEqual(PersonalizationRules.intensity(struggleFrequency: "many_times_daily"), "supportive")
    }

    // MARK: - Category mapping

    func test_primaryCategory() {
        XCTAssertEqual(PersonalizationRules.primaryCategory(desiredState: "calm"), "calm")
        XCTAssertEqual(PersonalizationRules.primaryCategory(desiredState: "confidence"), "confidence")
        XCTAssertEqual(PersonalizationRules.primaryCategory(desiredState: "focus"), "presence")
        XCTAssertEqual(PersonalizationRules.primaryCategory(desiredState: "self_love"), "self_love")
        XCTAssertNil(PersonalizationRules.primaryCategory(desiredState: nil))
    }

    func test_problemTypeBridge_onlyTrueCounterparts() {
        XCTAssertEqual(PersonalizationRules.problemTypeBridge(painPointId: "anxiety"), "anxiety")
        XCTAssertEqual(PersonalizationRules.problemTypeBridge(painPointId: "procrastination"), "procrastination")
        XCTAssertEqual(PersonalizationRules.problemTypeBridge(painPointId: "self_doubt"), "self_loathing")
        XCTAssertNil(PersonalizationRules.problemTypeBridge(painPointId: "stress"))
        XCTAssertNil(PersonalizationRules.problemTypeBridge(painPointId: "sleep"))
    }

    // MARK: - Selector

    private var pool: [Quote] {
        [
            Quote(id: "growth.calm.0", text: "calm"),
            Quote(id: "growth.presence.0", text: "presence"),
            Quote(id: "growth.growth.0", text: "growth"),
            Quote(id: "growth.rest.0", text: "rest"),
        ]
    }

    /// Random source replaying a fixed sequence (last value repeats).
    private func sequenceRandom(_ values: [Double]) -> () -> Double {
        var index = 0
        return {
            defer { index += 1 }
            return values[min(index, values.count - 1)]
        }
    }

    func test_selector_desiredStateAndPainPointMatchWins() {
        let profile = PersonalizationProfile(desiredState: "calm", painPointIds: ["anxiety"])
        let selection = PersonalizedNudgeSelector.select(
            profile: profile, pool: pool, band: .day, random: sequenceRandom([0.99]))
        XCTAssertEqual(selection?.quote.id, "growth.calm.0")
        XCTAssertEqual(selection?.reason, "desired_state_and_pain_point_match")
        XCTAssertEqual(selection?.candidateCount, 4)
        XCTAssertEqual(selection?.assignedProbability ?? 0, 0.9 + 0.1 / 4, accuracy: 1e-9)
    }

    func test_selector_cooldownExcludesRecentlyShown() {
        let profile = PersonalizationProfile(desiredState: "calm", painPointIds: ["anxiety"])
        let selection = PersonalizedNudgeSelector.select(
            profile: profile, pool: pool,
            shownAt: ["growth.calm.0": Date()], band: .day, random: sequenceRandom([0.99]))
        XCTAssertEqual(selection?.quote.id, "growth.presence.0")
    }

    func test_selector_morningExcludesRestUnlessSleepPain() {
        let noSleep = PersonalizationProfile(desiredState: "calm")
        let morning = PersonalizedNudgeSelector.select(
            profile: noSleep, pool: pool, band: .morning, random: sequenceRandom([0.99]))
        XCTAssertEqual(morning?.candidateCount, 3)

        let withSleep = PersonalizationProfile(desiredState: "calm", painPointIds: ["sleep"])
        let morningSleep = PersonalizedNudgeSelector.select(
            profile: withSleep, pool: pool, band: .morning, random: sequenceRandom([0.99]))
        XCTAssertEqual(morningSleep?.candidateCount, 4)
    }

    func test_selector_explorationRecordsExactProbability() {
        let profile = PersonalizationProfile()
        let selection = PersonalizedNudgeSelector.select(
            profile: profile, pool: pool, band: .day, random: sequenceRandom([0.05, 0.999]))
        // Ranked order for an empty profile is by id; index 3 is the last.
        XCTAssertEqual(selection?.quote.id, "growth.rest.0")
        XCTAssertEqual(selection?.assignedProbability ?? 0, 0.1 / 4, accuracy: 1e-9)
    }

    // MARK: - Records

    func test_profileCodableRoundTrip() throws {
        let profile = PersonalizationProfile(
            preferredName: "Aki", desiredState: "focus",
            painPointIds: ["stress", "sleep"], struggleFrequency: "daily",
            nudgeSlots: [NudgeSlot(hour: 17, minute: 30), NudgeSlot(hour: 21, minute: 30)],
            dailyFrequency: 2, timezoneIdentifier: "Asia/Tokyo",
            updatedAt: Date(timeIntervalSince1970: 1_700_000_000))
        let data = try JSONEncoder().encode(profile)
        let decoded = try JSONDecoder().decode(PersonalizationProfile.self, from: data)
        XCTAssertEqual(decoded, profile)
    }

    func test_decisionRecordRequiresProbability() throws {
        let record = DecisionPointRecord(
            recordKind: "decision", personId: "p1", deliveryId: "d1",
            decisionPointAt: "2026-11-14T00:00:00Z", available: true,
            treatmentAssigned: "growth.calm.0", assignedProbability: 0.925,
            messageId: "growth.calm.0", policyVersion: "rule_v1",
            source: "onboarding_preview", desiredState: "calm",
            painPointIds: ["anxiety"], struggleFrequency: "daily",
            candidateCount: 4, selectionReason: "desired_state_and_pain_point_match",
            proximalOutcome: nil, outcomeWindowSec: 1800)
        let data = try JSONEncoder().encode(record)
        let decoded = try JSONDecoder().decode(DecisionPointRecord.self, from: data)
        XCTAssertEqual(decoded, record)
        XCTAssertEqual(decoded.assignedProbability, 0.925)
    }

    // MARK: - Journey

    func test_initialJourney_includesPainPointsAndFrequencyBeforePreview() {
        XCTAssertEqual(
            OnboardingStep.initialJourney,
            [.goal, .painPoints, .struggleFreq, .planReveal, .nudgeTimes, .notifications]
        )
        XCTAssertEqual(OnboardingStep.goal.nextInitialStep, .painPoints)
        XCTAssertEqual(OnboardingStep.painPoints.nextInitialStep, .struggleFreq)
        XCTAssertEqual(OnboardingStep.struggleFreq.nextInitialStep, .planReveal)
        XCTAssertEqual(OnboardingStep.planReveal.nextInitialStep, .nudgeTimes)
        XCTAssertEqual(OnboardingStep.nudgeTimes.nextInitialStep, .notifications)
        XCTAssertNil(OnboardingStep.notifications.nextInitialStep)
    }
}
