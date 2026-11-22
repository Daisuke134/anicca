import XCTest
import SwiftUI
@testable import aniccaios

final class WordShareContentTests: XCTestCase {
    func testSnapshotContainsWordsBrandDatePromiseAndDestinations() {
        let date = Date(timeIntervalSince1970: 1795305600)
        let content = WordShareContent(quote: Quote(id: "generated:test", text: "ひと息。"), date: date)
        XCTAssertEqual(content.quote.text, "ひと息。")
        XCTAssertEqual(content.date, date)
        XCTAssertFalse(content.dateLabel.isEmpty)
        XCTAssertEqual(content.brand, "アニッチャ / Anicca")
        XCTAssertFalse(content.promise.isEmpty)
        for destination in ["#アニッチャ", "#AniccaWords", "@anicca.company"] {
            XCTAssertTrue(content.caption.contains(destination))
        }
    }

    func testSeparateAttemptsHaveSeparateIDsAndJSTDayIsStable() {
        let date = ISO8601DateFormatter().date(from: "2026-11-22T15:01:00Z")!
        let quote = Quote(id: "generated:test", text: "Words")
        let first = WordShareContent(quote: quote, date: date)
        let second = WordShareContent(quote: quote, date: date)
        XCTAssertNotEqual(first.id, second.id)
        XCTAssertEqual(first.dayJST, "2026-11-23")
        XCTAssertEqual(first.dayJST, second.dayJST)
    }

    func testExportKeepsEveryWordWithoutUnboundedLineBreaks() {
        let text = String(repeating: "a\n", count: 249)
        let content = WordShareContent(quote: Quote(id: "multiline", text: text))
        XCTAssertEqual(content.quote.text, text)
        XCTAssertEqual(content.exportText.split(separator: " ").count, 249)
        XCTAssertFalse(content.exportText.contains("\n"))
    }

    func testRolloutIsOffInAnUnconfiguredBundle() {
        XCTAssertFalse(WordShareContent.isEnabled(in: Bundle(for: Self.self), arguments: []))
    }

    @MainActor
    func testMaximumLengthWordRendersARealPortraitImage() {
        let content = WordShareContent(quote: Quote(id: "long", text: String(repeating: "言葉\n", count: 166)))
        let image = ShareImageRenderer.render(content: content, background: ThemeID.allCases[0])
        XCTAssertEqual(image?.size, CGSize(width: 1080, height: 1920))
        XCTAssertNotNil(image?.pngData())
    }
}
