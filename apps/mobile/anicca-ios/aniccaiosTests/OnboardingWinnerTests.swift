import XCTest
@testable import aniccaios

final class OnboardingWinnerTests: XCTestCase {
    func testJourneyCountsAndSelectionOrder() {
        XCTAssertEqual(OnboardingStep.journey(painPointIds: ["stress"]).count, 24)
        XCTAssertEqual(OnboardingStep.journey(painPointIds: ["sleep", "stress", "anxiety"], priorAttempts: ["books"]).count, 28)
        XCTAssertEqual(OnboardingStep.deepDiveSteps(painPointIds: ["sleep", "stress", "sleep"]), [.sleepReason, .bedtime, .wakeTime, .stressTrigger])
        XCTAssertEqual(OnboardingStep.priorAttempts.nextStep(painPointIds: [], priorAttempts: ["first_time"]), .startReason)
        XCTAssertEqual(OnboardingStep.notifications.nextInitialStep, .paywall)
    }

    func testOwnershipAnswersSurviveSyntheticProjectionWithoutPII() throws {
        var profile = PersonalizationProfile(preferredName: "Private Name", desiredState: "letting_go")
        var answers = AdaptiveAnswers()
        answers.set(.focusCategories, ids: ["relationships", "invalid"])
        answers.set(.themeChoice, ids: ["sageMist"])
        answers.set(.iconChoice, ids: ["AppIconOcean"])
        answers.set(.widgetPreview, ids: ["interested"])
        answers.set(.microPreview, ids: ["saved"])
        answers.birthDate = Date(timeIntervalSince1970: 12345)
        profile.adaptiveAnswers = answers
        let user = SyntheticUser(profile: profile, personId: "test")
        XCTAssertEqual(user.attributes["focus_categories"], ["relationships"])
        XCTAssertEqual(user.preferences["theme"], ["sageMist"])
        XCTAssertEqual(user.preferences["micro_preview_reaction"], ["saved"])
        XCTAssertEqual(user.conditioningProfile.desiredState, "letting_go")
        let json = String(decoding: try JSONEncoder().encode(user), as: UTF8.self)
        XCTAssertFalse(json.contains("Private Name"))
        XCTAssertFalse(json.contains("birthDate"))
    }

    func testPriorUsesAnswersAndLogsActualProbability() {
        var profile = PersonalizationProfile(desiredState: "calm")
        var answers = AdaptiveAnswers()
        answers.set(.beliefThemes, ids: ["self_trust"])
        answers.set(.moodBaseline, ids: ["heavy"])
        answers.set(.tone, ids: ["direct"])
        profile.adaptiveAnswers = answers
        let user = SyntheticUser(profile: profile, personId: "test")
        let pool = QuoteProvider.shared.all(preferredLanguage: .en)
        let distribution = OnboardingManagerPrior.distribution(user: user, pool: pool, band: .day)
        XCTAssertFalse(distribution.isEmpty)
        XCTAssertEqual(distribution.reduce(0) { $0 + $1.probability }, 1, accuracy: 0.000001)
        for candidate in distribution {
            // Heavy mood caps intensity to gentle but does not override the
            // tone the person chose (winner spec 2026-11-16 §6.1 row 6:
            // tone is an initial value biased at presentation, rule 3).
            XCTAssertEqual(AdaptiveAffirmationCatalog.traits(for: candidate.quote)?.tone, "direct")
            XCTAssertEqual(AdaptiveAffirmationCatalog.traits(for: candidate.quote)?.intensity, "gentle")
        }
        let selection = OnboardingManagerPrior.select(user: user, pool: pool, band: .day, random: { 0 })!
        XCTAssertEqual(selection.candidateIDs, distribution.map { $0.quote.id })
        XCTAssertEqual(selection.assignedProbability, distribution[0].probability)
        answers.set(.beliefThemes, ids: ["inner_peace"])
        profile.adaptiveAnswers = answers
        let changed = OnboardingManagerPrior.distribution(user: SyntheticUser(profile: profile, personId: "test"), pool: pool, band: .day)
        XCTAssertNotEqual(distribution.map(\.probability), changed.map(\.probability))
    }
}
