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

    init(service: ChatServicing, initialCursor: String? = nil) {
        self.service = service
        cursor = initialCursor
    }

    func sync(reason: SyncReason, targetMessageID: String? = nil) async throws -> ChatSyncResult {
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
}
