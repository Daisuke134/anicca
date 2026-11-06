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
        print("AffirmationCatalogTests: PASS (\(extra.count) supplemental quotes)")
    }
}
