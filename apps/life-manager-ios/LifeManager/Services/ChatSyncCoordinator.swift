import Foundation

enum SyncReason: Equatable, Sendable {
    case launch
    case foreground
    case manual
    case push
}

struct ChatSyncResult: Equatable, Sendable {
    let page: ChatPage
    let requestedCursor: String?
    let targetMessageID: String?
}

actor ChatSyncCoordinator {
    private let service: ChatServicing
    private var cursor: String?
    private var inFlight: Task<ChatPage, Error>?
#if DEBUG
    private var activeSyncWaiters = 0
#endif

    init(service: ChatServicing, initialCursor: String? = nil) {
        self.service = service
        cursor = initialCursor
    }

    func sync(reason: SyncReason, targetMessageID: String? = nil) async throws -> ChatSyncResult {
#if DEBUG
        activeSyncWaiters += 1
        defer { activeSyncWaiters -= 1 }
#endif
        _ = reason
        let requestedCursor = cursor
        let task: Task<ChatPage, Error>

        if let inFlight {
            task = inFlight
        } else {
            let fetchTask = Task {
                try await service.fetch(after: requestedCursor)
            }
            inFlight = fetchTask
            task = fetchTask
        }

        do {
            let page = try await task.value
            inFlight = nil
            if let nextCursor = page.nextCursor {
                cursor = nextCursor
            }
            return ChatSyncResult(
                page: page,
                requestedCursor: requestedCursor,
                targetMessageID: targetMessageID
            )
        } catch {
            inFlight = nil
            throw error
        }
    }

#if DEBUG
    func testingActiveSyncWaiters() -> Int {
        activeSyncWaiters
    }
#endif
}
