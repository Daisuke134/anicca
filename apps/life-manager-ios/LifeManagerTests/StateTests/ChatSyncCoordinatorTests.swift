import Foundation
import XCTest
@testable import LifeManager

@MainActor
final class ChatSyncCoordinatorTests: XCTestCase {
    func testAllReasonsFetchThroughOneMonotonicCursor() async throws {
        let service = SyncChatService(pages: [
            nil: ChatPage(messages: [SyncFixtures.message(id: "message-1")], nextCursor: "cursor-1", hasMore: true),
            "cursor-1": ChatPage(messages: [SyncFixtures.message(id: "message-2")], nextCursor: "cursor-2", hasMore: true),
            "cursor-2": ChatPage(messages: [SyncFixtures.message(id: "message-3")], nextCursor: "cursor-3", hasMore: true),
            "cursor-3": ChatPage(messages: [SyncFixtures.message(id: "message-4")], nextCursor: nil, hasMore: false)
        ])
        let coordinator = ChatSyncCoordinator(service: service)

        _ = try await coordinator.sync(reason: .launch)
        _ = try await coordinator.sync(reason: .foreground)
        _ = try await coordinator.sync(reason: .manual)
        let push = try await coordinator.sync(reason: .push, targetMessageID: "message-4")

        let cursors = await service.fetchCursors()
        XCTAssertEqual(cursors, [nil, "cursor-1", "cursor-2", "cursor-3"])
        XCTAssertEqual(push.targetMessageID, "message-4")
        XCTAssertEqual(push.requestedCursor, "cursor-3")
    }

    func testConcurrentReasonsCoalesceToOneFetch() async throws {
        let gate = SyncFetchGate()
        let page = ChatPage(messages: [SyncFixtures.message(id: "message-1")], nextCursor: "cursor-1", hasMore: true)
        let service = SyncChatService(pages: [nil: page], gate: gate)
        let coordinator = ChatSyncCoordinator(service: service)

        let launch = Task { try await coordinator.sync(reason: .launch) }
        await gate.waitUntilStarted()
        let foreground = Task { try await coordinator.sync(reason: .foreground) }
        while await coordinator.testingActiveSyncWaiters() < 2 {
            await Task.yield()
        }
        await gate.release(page)

        let launchResult = try await launch.value
        let foregroundResult = try await foreground.value

        XCTAssertEqual(launchResult, foregroundResult)
        let cursors = await service.fetchCursors()
        XCTAssertEqual(cursors, [nil])
    }

    func testFailedFetchDoesNotLoseTheLastSuccessfulCursor() async throws {
        let page = ChatPage(messages: [SyncFixtures.message(id: "message-1")], nextCursor: "cursor-1", hasMore: true)
        let recovery = ChatPage(messages: [SyncFixtures.message(id: "message-2")], nextCursor: "cursor-2", hasMore: true)
        let service = SyncChatService(
            pages: ["cursor-1": recovery],
            firstPage: page,
            errors: [APIError.transport("offline")]
        )
        let coordinator = ChatSyncCoordinator(service: service)

        _ = try await coordinator.sync(reason: .launch)
        do {
            _ = try await coordinator.sync(reason: .manual)
            XCTFail("expected the first cursor-1 fetch to fail")
        } catch {
            XCTAssertEqual(error as? APIError, .transport("offline"))
        }
        _ = try await coordinator.sync(reason: .foreground)

        let cursors = await service.fetchCursors()
        XCTAssertEqual(cursors, [nil, "cursor-1", "cursor-1"])
    }
}

private enum SyncFixtures {
    static func message(id: String) -> ChatMessage {
        ChatMessage(
            id: id,
            cursor: "cursor-\(id)",
            createdAt: Date(timeIntervalSince1970: id.last?.wholeNumberValue.map(TimeInterval.init) ?? 0),
            locale: .en,
            type: .system,
            text: id,
            userContent: CalendarUserContent(eventTitle: nil, eventLocation: nil),
            question: nil,
            route: nil,
            actions: []
        )
    }
}

private actor SyncChatService: ChatServicing {
    private var pages: [String?: ChatPage]
    private var cursors: [String?] = []
    private var errors: [Error]
    private let firstPage: ChatPage?
    private let gate: SyncFetchGate?

    init(
        pages: [String?: ChatPage],
        firstPage: ChatPage? = nil,
        errors: [Error] = [],
        gate: SyncFetchGate? = nil
    ) {
        self.pages = pages
        self.firstPage = firstPage
        self.errors = errors
        self.gate = gate
    }

    func fetch(after cursor: String?) async throws -> ChatPage {
        cursors.append(cursor)
        await gate?.started()
        if let gate {
            _ = await gate.waitForRelease()
        }
        if cursor == nil, let firstPage {
            return firstPage
        }
        if !errors.isEmpty {
            throw errors.removeFirst()
        }
        guard let page = pages[cursor] else {
            throw APIError.transport("missing page")
        }
        return page
    }

    func reply(questionID: String, text: String, idempotencyKey: UUID) async throws -> ChatMessage {
        throw APIError.transport("not used")
    }

    func fetchCursors() -> [String?] { cursors }
}

private actor SyncFetchGate {
    private var startedContinuation: CheckedContinuation<Void, Never>?
    private var releaseContinuation: CheckedContinuation<ChatPage, Never>?
    private var releasedPage: ChatPage?
    private var didStart = false

    func started() {
        didStart = true
        startedContinuation?.resume()
        startedContinuation = nil
    }

    func waitUntilStarted() async {
        if didStart { return }
        await withCheckedContinuation { continuation in
            startedContinuation = continuation
        }
    }

    func waitForRelease() async -> ChatPage {
        if let releasedPage {
            self.releasedPage = nil
            return releasedPage
        }
        return await withCheckedContinuation { continuation in
            releaseContinuation = continuation
        }
    }

    func release(_ page: ChatPage) {
        if let releaseContinuation {
            releaseContinuation.resume(returning: page)
            self.releaseContinuation = nil
        } else {
            releasedPage = page
        }
    }
}
