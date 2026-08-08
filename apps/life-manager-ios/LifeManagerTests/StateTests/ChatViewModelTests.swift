import Foundation
import XCTest
@testable import LifeManager

@MainActor
final class ChatViewModelTests: XCTestCase {
    func testInitialPageLoadsChronologicalMessagesAndCursor() async {
        let first = ChatFixtures.message(id: "message-1", type: .system, createdAt: "2026-08-10T08:00:00.000Z")
        let second = ChatFixtures.message(id: "message-2", type: .route, createdAt: "2026-08-10T08:10:00.000Z")
        let service = ChatTestService(pages: [
            nil: [ChatPage(messages: [first, second], nextCursor: "cursor-1", hasMore: true)]
        ])
        let viewModel = ChatViewModel(service: service)

        await viewModel.loadInitial()

        XCTAssertEqual(viewModel.messages.map(\.id), ["message-1", "message-2"])
        XCTAssertEqual(viewModel.nextCursor, "cursor-1")
        XCTAssertTrue(viewModel.hasMore)
        XCTAssertFalse(viewModel.isLoading)
        XCTAssertNil(viewModel.failure)
    }

    func testPaginationAppendsAndDeduplicatesByStableBackendID() async {
        let first = ChatFixtures.message(id: "message-1", type: .system, createdAt: "2026-08-10T08:00:00.000Z")
        let duplicate = ChatFixtures.message(id: "message-2", type: .route, createdAt: "2026-08-10T08:10:00.000Z")
        let newest = ChatFixtures.message(id: "message-3", type: .system, createdAt: "2026-08-10T08:20:00.000Z")
        let service = ChatTestService(pages: [
            nil: [ChatPage(messages: [first, duplicate], nextCursor: "cursor-1", hasMore: true)],
            "cursor-1": [ChatPage(messages: [duplicate, newest], nextCursor: nil, hasMore: false)]
        ])
        let viewModel = ChatViewModel(service: service)

        await viewModel.loadInitial()
        await viewModel.loadMore()

        XCTAssertEqual(viewModel.messages.map(\.id), ["message-1", "message-2", "message-3"])
        XCTAssertFalse(viewModel.hasMore)
        let cursors = await service.fetchCursors()
        XCTAssertEqual(cursors, [nil, "cursor-1"])
    }

    func testFailedInitialFetchShowsRetryableFailureAndRetryRecovers() async {
        let message = ChatFixtures.message(id: "message-1", type: .system, createdAt: "2026-08-10T08:00:00.000Z")
        let service = ChatTestService(
            pages: [nil: [ChatPage(messages: [message], nextCursor: nil, hasMore: false)]],
            fetchErrors: [APIError.transport("offline")]
        )
        let viewModel = ChatViewModel(service: service)

        await viewModel.loadInitial()

        XCTAssertEqual(viewModel.messages, [])
        XCTAssertEqual(viewModel.failure?.localizedMessageKey, "error.network")
        XCTAssertTrue(viewModel.failure?.retryAllowed == true)

        await viewModel.retry()

        XCTAssertEqual(viewModel.messages.map(\.id), ["message-1"])
        XCTAssertNil(viewModel.failure)
    }

    func testPaginationPreservesExplicitScrollAnchor() async {
        let first = ChatFixtures.message(id: "message-1", type: .system, createdAt: "2026-08-10T08:00:00.000Z")
        let second = ChatFixtures.message(id: "message-2", type: .system, createdAt: "2026-08-10T08:10:00.000Z")
        let service = ChatTestService(pages: [
            nil: [ChatPage(messages: [first], nextCursor: "cursor-1", hasMore: true)],
            "cursor-1": [
                ChatPage(messages: [second], nextCursor: nil, hasMore: false),
                ChatPage(messages: [second], nextCursor: nil, hasMore: false)
            ]
        ])
        let viewModel = ChatViewModel(service: service)

        await viewModel.loadInitial()
        viewModel.rememberScrollAnchor("message-1")
        await viewModel.loadMore()

        XCTAssertEqual(viewModel.scrollAnchorID, "message-1")
        XCTAssertEqual(viewModel.messages.map(\.id), ["message-1", "message-2"])
    }

    func testForegroundSyncPreservesAnchorAndPushSyncTargetsStableMessage() async {
        let first = ChatFixtures.message(id: "message-1", type: .system, createdAt: "2026-08-10T08:00:00.000Z")
        let second = ChatFixtures.message(id: "message-2", type: .route, createdAt: "2026-08-10T08:10:00.000Z")
        let service = ChatTestService(pages: [
            nil: [ChatPage(messages: [first], nextCursor: "cursor-1", hasMore: true)],
            "cursor-1": [
                ChatPage(messages: [second], nextCursor: nil, hasMore: false),
                ChatPage(messages: [second], nextCursor: nil, hasMore: false)
            ]
        ])
        let viewModel = ChatViewModel(service: service)

        await viewModel.loadInitial()
        viewModel.rememberScrollAnchor("message-1")
        await viewModel.syncFromForeground()
        XCTAssertEqual(viewModel.scrollAnchorID, "message-1")

        await viewModel.syncFromPush(targetMessageID: "message-2")
        XCTAssertEqual(viewModel.scrollAnchorID, "message-2")
        XCTAssertEqual(viewModel.messages.map(\.id), ["message-1", "message-2"])
    }

    func testComposerIsAvailableOnlyForAnOpenQuestion() async {
        let question = ChatFixtures.message(
            id: "question-message",
            type: .question,
            createdAt: "2026-08-10T08:00:00.000Z",
            question: ChatQuestion(id: "question-1", prompt: "Where are you starting from?")
        )
        let service = ChatTestService(pages: [
            nil: [ChatPage(messages: [question], nextCursor: nil, hasMore: false)]
        ])
        let viewModel = ChatViewModel(service: service)

        await viewModel.loadInitial()

        XCTAssertTrue(viewModel.canReply)
        XCTAssertEqual(viewModel.openQuestion?.id, "question-1")
        XCTAssertTrue(viewModel.composerVisible)

        await viewModel.reply(text: "Home")

        XCTAssertFalse(viewModel.canReply)
        XCTAssertFalse(viewModel.composerVisible)
        let replyCount = await service.replyCount()
        XCTAssertEqual(replyCount, 1)
    }

    func testStaleReplyIsNotInsertedAfterChatRefreshChangesOpenQuestion() async {
        let question = ChatFixtures.message(
            id: "question-message",
            type: .question,
            createdAt: "2026-08-10T08:00:00.000Z",
            question: ChatQuestion(id: "question-1", prompt: "Where are you starting from?")
        )
        let refreshed = ChatFixtures.message(id: "message-2", type: .system, createdAt: "2026-08-10T08:10:00.000Z")
        let reply = ChatFixtures.message(id: "reply-1", type: .system, createdAt: "2026-08-10T08:11:00.000Z")
        let gate = ReplyGate()
        let service = ChatTestService(
            pages: [
                nil: [
                    ChatPage(messages: [question], nextCursor: nil, hasMore: false),
                    ChatPage(messages: [refreshed], nextCursor: nil, hasMore: false)
                ]
            ],
            replyGate: gate
        )
        let viewModel = ChatViewModel(service: service)

        await viewModel.loadInitial()
        let replyTask = Task { await viewModel.reply(text: "Home") }
        await gate.waitUntilReplyStarted()

        await viewModel.refresh()
        await gate.release(reply)
        await replyTask.value

        XCTAssertTrue(viewModel.staleReply)
        XCTAssertEqual(viewModel.messages.map(\.id), ["message-2"])
        XCTAssertFalse(viewModel.isReplying)
    }
}

private enum ChatFixtures {
    static func message(
        id: String,
        type: ChatMessageType,
        createdAt: String,
        question: ChatQuestion? = nil
    ) -> ChatMessage {
        ChatMessage(
            id: id,
            cursor: "cursor-\(id)",
            createdAt: Date.iso8601(createdAt),
            locale: .en,
            type: type,
            text: id,
            userContent: CalendarUserContent(eventTitle: nil, eventLocation: nil),
            question: question,
            route: nil,
            actions: []
        )
    }
}

private actor ChatTestService: ChatServicing {
    private var pages: [String?: [ChatPage]]
    private var fetchErrors: [Error]
    private var cursors: [String?] = []
    private var replies = 0
    private let replyGate: ReplyGate?

    init(
        pages: [String?: [ChatPage]],
        fetchErrors: [Error] = [],
        replyGate: ReplyGate? = nil
    ) {
        self.pages = pages
        self.fetchErrors = fetchErrors
        self.replyGate = replyGate
    }

    func fetch(after cursor: String?) async throws -> ChatPage {
        cursors.append(cursor)
        if !fetchErrors.isEmpty {
            throw fetchErrors.removeFirst()
        }
        guard var queuedPages = pages[cursor], !queuedPages.isEmpty else {
            throw APIError.transport("missing page")
        }
        let page = queuedPages.removeFirst()
        pages[cursor] = queuedPages
        return page
    }

    func reply(questionID: String, text: String, idempotencyKey: UUID) async throws -> ChatMessage {
        replies += 1
        if let replyGate {
            return await replyGate.waitForReply()
        }
        return ChatFixtures.message(id: "reply-\(questionID)", type: .system, createdAt: "2026-08-10T08:01:00.000Z")
    }

    func fetchCursors() -> [String?] { cursors }
    func replyCount() -> Int { replies }
}

private actor ReplyGate {
    private var replyContinuation: CheckedContinuation<ChatMessage, Never>?
    private var startedContinuation: CheckedContinuation<Void, Never>?
    private var didStart = false

    func waitForReply() async -> ChatMessage {
        didStart = true
        startedContinuation?.resume()
        startedContinuation = nil
        return await withCheckedContinuation { continuation in
            replyContinuation = continuation
        }
    }

    func waitUntilReplyStarted() async {
        if didStart { return }
        await withCheckedContinuation { continuation in
            startedContinuation = continuation
        }
    }

    func release(_ message: ChatMessage) {
        replyContinuation?.resume(returning: message)
        replyContinuation = nil
    }
}
