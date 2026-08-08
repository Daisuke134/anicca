import Foundation
import XCTest
@testable import LifeManager

final class ChatReceiptPresentationTests: XCTestCase {
    func testTravelReceiptAccessibilityIDsUseSemanticKeyAndStableMessageID() {
        let confirmed = ChatReceiptFixtures.message(
            id: "message:v1:confirmed",
            semanticKey: "chat.travel_block_confirmed"
        )
        let notAdded = ChatReceiptFixtures.message(
            id: "message:v1:not-added",
            semanticKey: "chat.travel_block_not_added"
        )

        XCTAssertEqual(
            ChatMessageAccessibility.identifier(for: confirmed),
            "calendar.travelBlock.confirmed.message:v1:confirmed"
        )
        XCTAssertEqual(
            ChatMessageAccessibility.identifier(for: notAdded),
            "calendar.travelBlock.notAdded.message:v1:not-added"
        )
    }

    func testNonReceiptMessagesKeepTheExistingChatMessageID() {
        let legacy = ChatReceiptFixtures.message(id: "message:v1:legacy", semanticKey: nil)
        let unknown = ChatReceiptFixtures.message(id: "message:v1:unknown", semanticKey: "chat.future_key")

        XCTAssertEqual(
            ChatMessageAccessibility.identifier(for: legacy),
            "chat.message.message:v1:legacy"
        )
        XCTAssertEqual(
            ChatMessageAccessibility.identifier(for: unknown),
            "chat.message.message:v1:unknown"
        )
    }

    func testReceiptPresentationDoesNotReplaceServerLocalizedCopy() {
        let english = ChatReceiptFixtures.message(
            id: "message:v1:confirmed-en",
            semanticKey: "chat.travel_block_confirmed",
            locale: .en,
            text: "Travel time was added to your Calendar and verified."
        )
        let japanese = ChatReceiptFixtures.message(
            id: "message:v1:confirmed-ja",
            semanticKey: "chat.travel_block_confirmed",
            locale: .ja,
            text: "移動時間をカレンダーに追加し、確認できました。"
        )

        XCTAssertEqual(english.text, "Travel time was added to your Calendar and verified.")
        XCTAssertEqual(japanese.text, "移動時間をカレンダーに追加し、確認できました。")
        XCTAssertEqual(english.locale, .en)
        XCTAssertEqual(japanese.locale, .ja)
    }
}

private enum ChatReceiptFixtures {
    static func message(
        id: String,
        semanticKey: String?,
        locale: ProductLocale = .en,
        text: String = "Server-projected chat message"
    ) -> ChatMessage {
        ChatMessage(
            id: id,
            cursor: "cursor:\(id)",
            createdAt: Date.iso8601("2026-08-10T08:31:00.000Z"),
            locale: locale,
            type: .system,
            text: text,
            userContent: CalendarUserContent(eventTitle: nil, eventLocation: nil),
            question: nil,
            route: nil,
            actions: [],
            semanticKey: semanticKey
        )
    }
}
