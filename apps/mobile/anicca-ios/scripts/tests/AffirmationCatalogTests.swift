import Foundation

@main
struct AffirmationCatalogTests {
    static func main() throws {
        let url = URL(fileURLWithPath: "apps/mobile/anicca-ios/aniccaios/Resources/SupplementalAffirmations.json")
        let extra = try QuoteProvider.supplementalQuotes(at: url)
        guard extra.count >= 400, Set(extra.map(\.id)).count == extra.count,
              Set(extra.map(\.text)).count == extra.count,
              Set(extra.map(\.categoryID)).count >= 12,
              extra.allSatisfy({ !$0.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }) else {
            print("FAIL: supplemental catalog must add 400 unique, categorized affirmations")
            exit(1)
        }
        let pool = (0..<10).flatMap { i in
            [Quote(id: "growth.calm.\(i)", text: "Calm \(i)"),
             Quote(id: "growth.confidence.\(i)", text: "Confidence \(i)"),
             Quote(id: "growth.rest.\(i)", text: "Rest \(i)")]
        }
        let ranked = QuoteProvider.recommendations(from: pool, goals: ["calm"], likedIDs: ["growth.confidence.0"], recentIDs: ["growth.calm.0"])
        guard ranked.count == 29, !ranked.contains(where: { $0.id == "growth.calm.0" }),
              ranked.prefix(5).filter({ $0.categoryID == "rest" }).count == 1,
              Set(ranked.map(\.id)).count == ranked.count else { exit(2) }
        let exhausted = QuoteProvider.recommendations(from: [pool[0]], goals: [], likedIDs: [], recentIDs: [pool[0].id])
        guard exhausted.count == 1 else { exit(3) }
        let remaining = pool.filter { $0.id != "growth.confidence.0" }
        let likedRanking = QuoteProvider.recommendations(from: remaining, goals: [], likedIDs: ["growth.confidence.0"], recentIDs: [])
        guard likedRanking.prefix(4).allSatisfy({ $0.categoryID == "confidence" }) else {
            print("FAIL: a like outside the remaining candidate pool must still personalize the next batch")
            exit(4)
        }
        // Onboarding personalization v1 (1.9.10): the struggles answer must steer the feed.
        // Every ProblemType stored from onboarding maps to at least one quote category.
        for problem in ["self_loathing", "procrastination", "anxiety", "rumination", "anger"] {
            guard let categories = QuoteProvider.problemCategories[problem], !categories.isEmpty else {
                print("FAIL: problem \(problem) has no quote category mapping")
                exit(5)
            }
        }
        // anxiety -> calm: with no goals/likes, the first batch must lead with calm quotes.
        let anxietyRanking = QuoteProvider.recommendations(from: pool, goals: [], problems: ["anxiety"], likedIDs: [], recentIDs: [])
        guard anxietyRanking.count == pool.count,
              anxietyRanking.prefix(4).allSatisfy({ $0.categoryID == "calm" }) else {
            print("FAIL: onboarding struggle (anxiety) must lead the feed with calm quotes")
            exit(6)
        }
        // No answers -> unchanged behaviour (no crash, full pool returned).
        let unpersonalized = QuoteProvider.recommendations(from: pool, goals: [], problems: [], likedIDs: [], recentIDs: [])
        guard unpersonalized.count == pool.count else {
            print("FAIL: empty problems must return the full pool")
            exit(7)
        }
        print("AffirmationCatalogTests: PASS (\(extra.count) supplemental quotes)")
    }
}
