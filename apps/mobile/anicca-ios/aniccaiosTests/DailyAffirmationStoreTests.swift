import XCTest
@testable import aniccaios

@MainActor
final class DailyAffirmationStoreTests: XCTestCase {
    func testFirstInterventionSurvivesRelaunchWithoutReselection() {
        withDefaults { defaults in
            let date = Date(timeIntervalSince1970: 1_800_000_000)
            let intervention = Quote(id: "q013", text: "I can be kind to myself.")
            DailyAffirmationStore(defaults: defaults).seed(intervention, language: "en", now: date)
            var selections = 0
            let restored = DailyAffirmationStore(defaults: defaults)
            let result = restored.todayQuote(language: "en", now: date) {
                selections += 1
                return Quote(id: "q014", text: "A different quote.")
            }
            XCTAssertEqual(result, intervention)
            XCTAssertEqual(selections, 0)
        }
    }

    func testNewDaySelectsOnceAndLanguageChangeRefreshes() {
        withDefaults { defaults in
            var calendar = Calendar(identifier: .gregorian)
            calendar.timeZone = TimeZone(secondsFromGMT: 0)!
            let date = Date(timeIntervalSince1970: 1_800_000_000)
            let nextDay = calendar.date(byAdding: .day, value: 1, to: date)!
            let first = Quote(id: "q013", text: "First")
            let second = Quote(id: "q014", text: "Second")
            let translated = Quote(id: "q014", text: "二つ目")
            let store = DailyAffirmationStore(defaults: defaults)
            store.seed(first, language: "en", now: date)
            var selections = 0
            XCTAssertEqual(store.todayQuote(language: "en", now: nextDay, calendar: calendar) {
                selections += 1
                return second
            }, second)
            XCTAssertEqual(store.todayQuote(language: "en", now: nextDay, calendar: calendar) {
                selections += 1
                return first
            }, second)
            XCTAssertEqual(selections, 1)
            XCTAssertEqual(store.todayQuote(language: "ja", now: nextDay, calendar: calendar) { translated }, translated)
        }
    }

    func testNotificationReplacesTodayAndSurvivesRelaunch() {
        withDefaults { defaults in
            let date = Date(timeIntervalSince1970: 1_800_000_000)
            let store = DailyAffirmationStore(defaults: defaults)
            store.seed(Quote(id: "q013", text: "Daily words"), language: "en", now: date)
            let notification = Quote(id: "notification:unknown", text: "The exact words I tapped.")
            store.seed(notification, language: "en", now: date)
            XCTAssertEqual(DailyAffirmationStore(defaults: defaults).todayQuote(language: "en", now: date) { nil }, notification)
        }
    }

    func testSavedQuoteKeepsItsThemeAndLegacyLikesStillLoad() {
        withDefaults { defaults in
            defaults.set(["q013"], forKey: "anicca.liked.ids")
            let catalogQuote = Quote(id: "q013", text: "Legacy favorite")
            let savedQuote = Quote(id: "q014", text: "Saved on sand")
            let store = LikedQuotesStore(defaults: defaults)
            XCTAssertEqual(store.savedQuotes(in: [catalogQuote]), [catalogQuote])
            XCTAssertEqual(store.themeID(for: catalogQuote.id), "sageMist")
            XCTAssertTrue(store.toggle(savedQuote, themeID: "sandWave"))
            defaults.set("midnightDusk", forKey: "anicca.theme")
            let restored = LikedQuotesStore(defaults: defaults)
            XCTAssertEqual(restored.themeID(for: savedQuote.id), "sandWave")
            XCTAssertTrue(restored.savedQuotes(in: []).contains(savedQuote))
            XCTAssertFalse(restored.toggle(savedQuote))
            XCTAssertFalse(LikedQuotesStore(defaults: defaults).isLiked(savedQuote.id))
        }
    }

    private func withDefaults(_ body: (UserDefaults) -> Void) {
        let suite = "DailyAffirmationStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        body(defaults)
    }
}
