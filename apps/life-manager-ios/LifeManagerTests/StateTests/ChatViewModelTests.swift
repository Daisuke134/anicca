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

    func testPushDuringInitialSyncIsRetriedAndAnchorsStableMessage() async {
        let first = ChatFixtures.message(id: "message-1", type: .system, createdAt: "2026-08-10T08:00:00.000Z")
        let pushed = ChatFixtures.message(id: "message-2", type: .system, createdAt: "2026-08-10T08:10:00.000Z")
        let gate = FetchGate()
        let service = ChatTestService(
            pages: [
                nil: [ChatPage(messages: [first], nextCursor: "cursor-1", hasMore: true)],
                "cursor-1": [ChatPage(messages: [pushed], nextCursor: nil, hasMore: false)]
            ],
            fetchGate: gate
        )
        let viewModel = ChatViewModel(service: service)

        let initialTask = Task { await viewModel.loadInitial() }
        await gate.waitUntilFirstFetchStarted()
        await viewModel.syncFromPush(targetMessageID: pushed.id)
        await gate.releaseFirstFetch()
        await initialTask.value

        let cursors = await service.fetchCursors()
        XCTAssertEqual(cursors, [nil, "cursor-1"])
        XCTAssertEqual(viewModel.scrollAnchorID, pushed.id)
        XCTAssertEqual(viewModel.messages.map(\.id), [first.id, pushed.id])
    }

    func testLocaleChangeResetsProjectionAndFetchesFromBeginning() async {
        let english = ChatFixtures.message(id: "english-message", type: .system, createdAt: "2026-08-10T08:00:00.000Z")
        let japanese = ChatFixtures.message(id: "japanese-message", type: .system, createdAt: "2026-08-10T08:10:00.000Z")
        let service = ChatTestService(pages: [
            nil: [
                ChatPage(messages: [english], nextCursor: "cursor-en", hasMore: true),
                ChatPage(messages: [japanese], nextCursor: nil, hasMore: false)
            ],
            "cursor-en": [ChatPage(messages: [], nextCursor: nil, hasMore: false)]
        ])
        let viewModel = ChatViewModel(service: service)

        await viewModel.loadInitial()
        await viewModel.resetForLocaleChange()

        XCTAssertEqual(viewModel.messages.map(\.id), [japanese.id])
        XCTAssertFalse(viewModel.hasMore)
        let cursors = await service.fetchCursors()
        XCTAssertEqual(cursors, [nil, nil])
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

    func testReplyRefreshesDurableOutboxAfterQuestionReply() async {
        let question = ChatFixtures.message(
            id: "question-message",
            type: .question,
            createdAt: "2026-08-10T08:00:00.000Z",
            question: ChatQuestion(id: "question-1", prompt: "Where are you starting from?")
        )
        let durableReply = ChatFixtures.message(
            id: "durable-reply",
            type: .system,
            createdAt: "2026-08-10T08:01:00.000Z"
        )
        let service = ChatTestService(pages: [
            nil: [
                ChatPage(messages: [question], nextCursor: "cursor-question", hasMore: false)
            ],
            "cursor-question": [
                ChatPage(messages: [durableReply], nextCursor: "cursor-reply", hasMore: false)
            ]
        ])
        let viewModel = ChatViewModel(service: service)

        await viewModel.loadInitial()
        await viewModel.reply(text: "Home")

        XCTAssertEqual(viewModel.messages.map(\.id), [question.id, durableReply.id])
        let cursors = await service.fetchCursors()
        XCTAssertEqual(cursors, [nil, "cursor-question"])
    }

    func testAmbiguousReplyRetainsTextAndIdempotencyKeyForRetry() async {
        let question = ChatFixtures.message(
            id: "question-message",
            type: .question,
            createdAt: "2026-08-10T08:00:00.000Z",
            question: ChatQuestion(id: "question-1", prompt: "Where are you starting from?")
        )
        let service = RetryingChatService(question: question)
        let store = TestOperationRetryStore()
        let viewModel = ChatViewModel(service: service, retryStore: store)

        await viewModel.loadInitial()
        await viewModel.reply(text: "Home")

        XCTAssertEqual(viewModel.composerText, "Home")
        let pendingAfterFailure = await store.pending(for: .reply)
        XCTAssertNotNil(pendingAfterFailure)

        await viewModel.reply()

        XCTAssertEqual(viewModel.composerText, "")
        let pendingAfterSuccess = await store.pending(for: .reply)
        XCTAssertNil(pendingAfterSuccess)
        let keys = await service.keys()
        XCTAssertEqual(keys.count, 2)
        XCTAssertEqual(keys.first, keys.last)
    }

    func testStaleReplyIsNotInsertedAfterChatRefreshChangesOpenQuestion() async {
        let question = ChatFixtures.message(
            id: "question-message",
            type: .question,
            createdAt: "2026-08-10T08:00:00.000Z",
            question: ChatQuestion(id: "question-1", prompt: "Where are you starting from?")
        )
        let refreshed = ChatFixtures.message(id: "message-2", type: .system, createdAt: "2026-08-10T08:10:00.000Z")
        let reply = QuestionReplyReceipt(status: "answered", questionID: question.id, analysis: nil)
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
    private let fetchGate: FetchGate?

    init(
        pages: [String?: [ChatPage]],
        fetchErrors: [Error] = [],
        replyGate: ReplyGate? = nil,
        fetchGate: FetchGate? = nil
    ) {
        self.pages = pages
        self.fetchErrors = fetchErrors
        self.replyGate = replyGate
        self.fetchGate = fetchGate
    }

    func fetch(after cursor: String?) async throws -> ChatPage {
        cursors.append(cursor)
        await fetchGate?.waitForFirstFetch()
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

    func reply(questionID: String, text: String, idempotencyKey: UUID) async throws -> QuestionReplyReceipt {
        replies += 1
        if let replyGate {
            return await replyGate.waitForReply()
        }
        return QuestionReplyReceipt(status: "answered", questionID: questionID, analysis: nil)
    }

    func fetchCursors() -> [String?] { cursors }
    func replyCount() -> Int { replies }
}

private actor RetryingChatService: ChatServicing {
    private let question: ChatMessage
    private var attempts = 0
    private var recordedKeys: [UUID] = []

    init(question: ChatMessage) { self.question = question }

    func fetch(after cursor: String?) async throws -> ChatPage {
        ChatPage(messages: [question], nextCursor: nil, hasMore: false)
    }

    func reply(questionID: String, text: String, idempotencyKey: UUID) async throws -> QuestionReplyReceipt {
        attempts += 1
        recordedKeys.append(idempotencyKey)
        if attempts == 1 { throw APIError.transport("offline") }
        return QuestionReplyReceipt(status: "answered", questionID: questionID, analysis: nil)
    }

    func keys() -> [UUID] { recordedKeys }
}

private actor FetchGate {
    private var startedContinuation: CheckedContinuation<Void, Never>?
    private var releaseContinuation: CheckedContinuation<Void, Never>?
    private var didStart = false

    func waitForFirstFetch() async {
        guard !didStart else { return }
        didStart = true
        startedContinuation?.resume()
        startedContinuation = nil
        await withCheckedContinuation { continuation in
            releaseContinuation = continuation
        }
    }

    func waitUntilFirstFetchStarted() async {
        if didStart { return }
        await withCheckedContinuation { continuation in
            startedContinuation = continuation
        }
    }

    func releaseFirstFetch() {
        releaseContinuation?.resume()
        releaseContinuation = nil
    }
}

private actor ReplyGate {
    private var replyContinuation: CheckedContinuation<QuestionReplyReceipt, Never>?
    private var startedContinuation: CheckedContinuation<Void, Never>?
    private var didStart = false

    func waitForReply() async -> QuestionReplyReceipt {
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

    func release(_ receipt: QuestionReplyReceipt) {
        replyContinuation?.resume(returning: receipt)
        replyContinuation = nil
    }
}
