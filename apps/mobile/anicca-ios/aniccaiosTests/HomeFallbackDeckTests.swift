import XCTest
@testable import aniccaios

/// Regression tests for the 1.11.0 blank-home bug: the Manager engine
/// rejected every app request (HTTP 422) and the home suppressed all words
/// instead of falling back. The bundled fallback deck must always yield
/// real words — backend normal-but-`none`, backend error, and fully
/// offline all land on this deck.
final class HomeFallbackDeckTests: XCTestCase {
    private func date(_ year: Int, _ month: Int, _ day: Int) -> Date {
        Calendar(identifier: .gregorian).date(from: DateComponents(year: year, month: month, day: day))!
    }

    func testFallbackDeckIsNeverEmptyInAnyLanguage() {
        for language in [LanguagePreference.en, .ja, .es, .de, .fr, .ptBR] {
            let deck = HomeFallbackDeck.quotes(language: language, date: date(2026, 11, 23))
            XCTAssertFalse(deck.isEmpty, "fallback deck must not be empty for \(language)")
            XCTAssertTrue(deck.allSatisfy { !$0.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty },
                          "every fallback card must carry real words for \(language)")
        }
    }

    func testFallbackDeckStartsWithTodaysWord() {
        let day = date(2026, 11, 23)
        let deck = HomeFallbackDeck.quotes(language: .en, date: day)
        XCTAssertEqual(deck.first?.text, QuoteProvider.shared.todayQuote(preferredLanguage: .en, date: day),
                       "first fallback card is the established daily word")
    }

    func testFallbackDeckRotatesAcrossDays() {
        let first = HomeFallbackDeck.quotes(language: .en, date: date(2026, 11, 23)).first
        let next = HomeFallbackDeck.quotes(language: .en, date: date(2026, 11, 24)).first
        XCTAssertNotNil(first)
        XCTAssertNotNil(next)
        XCTAssertNotEqual(first?.id, next?.id, "the living home must keep changing words day to day")
    }

    func testFallbackDeckHasEnoughCardsToRotate() {
        let deck = HomeFallbackDeck.quotes(language: .en, date: date(2026, 11, 23))
        XCTAssertGreaterThan(deck.count, 1, "auto-advance needs more than one card")
        XCTAssertEqual(Set(deck.map(\.id)).count, deck.count, "no duplicate cards in one deck")
    }
}
