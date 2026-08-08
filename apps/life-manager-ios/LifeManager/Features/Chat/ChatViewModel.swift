import Foundation
import Observation

@MainActor
@Observable
final class ChatViewModel {
    private let service: ChatServicing
    private let coordinator: ChatSyncCoordinator
    private let retryStore: OperationRetryStoring
    private var fetchGeneration = 0
    private var replyInvalidationGeneration = 0
    private var answeredQuestionIDs = Set<String>()
    private var pendingPushTargetMessageID: String?

    private(set) var messages: [ChatMessage] = []
    private(set) var nextCursor: String?
    private(set) var hasMore = false
    private(set) var isLoading = false
    private(set) var isLoadingMore = false
    private(set) var isReplying = false
    private(set) var failure: AppErrorState?
    private(set) var staleReply = false
    private(set) var scrollAnchorID: String?

    var composerText = ""

    init(
        service: ChatServicing,
        retryStore: OperationRetryStoring = UserDefaultsOperationRetryStore()
    ) {
        self.service = service
        coordinator = ChatSyncCoordinator(service: service)
        self.retryStore = retryStore
    }

    var openQuestion: ChatQuestion? {
        messages.reversed().compactMap { message in
            guard
                message.type == .question,
                let question = message.question,
                !answeredQuestionIDs.contains(question.id)
            else {
                return nil
            }
            return question
        }.first
    }

    var canReply: Bool {
        openQuestion != nil && !isReplying
    }

    var composerVisible: Bool {
        openQuestion != nil
    }

    func loadInitial() async {
        guard !isLoading else { return }
        await sync(reason: .launch)
    }

    func refresh() async {
        guard !isLoading else { return }
        await sync(reason: .manual)
    }

    func syncFromForeground() async {
        guard !isLoading else { return }
        await sync(reason: .foreground)
    }

    func resetForLocaleChange() async {
        fetchGeneration &+= 1
        replyInvalidationGeneration &+= 1
        pendingPushTargetMessageID = nil
        answeredQuestionIDs.removeAll()
        messages = []
        nextCursor = nil
        hasMore = false
        failure = nil
        staleReply = false
        scrollAnchorID = nil
        composerText = ""
        isLoading = false
        isLoadingMore = false
        await coordinator.reset()
        await sync(reason: .launch)
    }

    func clearProjection() async {
        fetchGeneration &+= 1
        replyInvalidationGeneration &+= 1
        pendingPushTargetMessageID = nil
        answeredQuestionIDs.removeAll()
        messages = []
        nextCursor = nil
        hasMore = false
        failure = nil
        staleReply = false
        scrollAnchorID = nil
        composerText = ""
        isLoading = false
        isLoadingMore = false
        await coordinator.reset()
    }

    func syncFromPush(targetMessageID: String) async {
        guard !isLoading else {
            pendingPushTargetMessageID = targetMessageID
            return
        }
        await sync(reason: .push, targetMessageID: targetMessageID)
    }

    func retry() async {
        await refresh()
    }

    func loadMore() async {
        guard
            !isLoadingMore,
            !isLoading,
            hasMore,
            nextCursor != nil
        else {
            return
        }

        isLoadingMore = true
        failure = nil
        let generation = fetchGeneration
        let existingAnchor = scrollAnchorID ?? messages.first?.id

        do {
            let result = try await coordinator.sync(reason: .manual)
            guard generation == fetchGeneration else {
                isLoadingMore = false
                return
            }
            merge(result.page.messages, replacing: result.requestedCursor == nil)
            nextCursor = result.page.nextCursor
            hasMore = result.page.hasMore
            if scrollAnchorID == nil {
                scrollAnchorID = existingAnchor
            }
        } catch {
            if generation == fetchGeneration {
                failure = AppErrorState(error: error)
            }
        }

        isLoadingMore = false
    }

    func rememberScrollAnchor(_ messageID: String?) {
        scrollAnchorID = messageID
    }

    func reply(text: String? = nil) async {
        guard let question = openQuestion else { return }
        let pending = await retryStore.pending(for: .reply)
        let pendingInput = pending.flatMap { operation in
            operation.input.flatMap { try? JSONDecoder.lifeManager.decode(PendingReplyInput.self, from: $0) }
        }
        let canReusePending = text == nil && pendingInput?.questionID == question.id
        let value = (canReusePending ? pendingInput?.text : (text ?? composerText))?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard !value.isEmpty, !isReplying else { return }

        let operationKey: UUID
        if canReusePending, let pending {
            operationKey = pending.idempotencyKey
        } else {
            operationKey = UUID()
            let input = try? JSONEncoder.lifeManager.encode(
                PendingReplyInput(questionID: question.id, text: value)
            )
            await retryStore.save(
                .reply,
                value: PendingOperation(idempotencyKey: operationKey, input: input)
            )
        }

        let generation = fetchGeneration
        let replyInvalidation = replyInvalidationGeneration
        let questionID = question.id
        composerText = ""
        isReplying = true
        failure = nil
        staleReply = false

        do {
            _ = try await service.reply(
                questionID: questionID,
                text: value,
                idempotencyKey: operationKey
            )
            await retryStore.clear(.reply)
            if replyInvalidation != replyInvalidationGeneration {
                staleReply = true
            } else {
                answeredQuestionIDs.insert(questionID)
                if generation != fetchGeneration {
                    await coordinator.reset()
                }
                await sync(reason: .manual)
            }
        } catch {
            if MutationRetryPolicy.shouldRetain(after: error) {
                composerText = value
            } else {
                await retryStore.clear(.reply)
                composerText = ""
            }
            failure = AppErrorState(error: error)
        }

        isReplying = false
    }

    private func sync(reason: SyncReason, targetMessageID: String? = nil) async {
        isLoading = true
        failure = nil
        staleReply = false
        fetchGeneration &+= 1
        let generation = fetchGeneration

        do {
            let result = try await coordinator.sync(reason: reason, targetMessageID: targetMessageID)
            guard generation == fetchGeneration else {
                return
            }
            merge(result.page.messages, replacing: result.requestedCursor == nil)
            nextCursor = result.page.nextCursor
            hasMore = result.page.hasMore
            if let target = result.targetMessageID, messages.contains(where: { $0.id == target }) {
                scrollAnchorID = target
            }
        } catch {
            if generation == fetchGeneration {
                failure = AppErrorState(error: error)
            }
        }

        guard generation == fetchGeneration else { return }
        isLoading = false
        await drainPendingPushIfNeeded()
    }

    private func drainPendingPushIfNeeded() async {
        guard let targetMessageID = pendingPushTargetMessageID else { return }
        pendingPushTargetMessageID = nil

        if messages.contains(where: { $0.id == targetMessageID }) {
            scrollAnchorID = targetMessageID
            return
        }

        await sync(reason: .push, targetMessageID: targetMessageID)
    }

    private func merge(_ incoming: [ChatMessage], replacing: Bool) {
        let source = replacing ? incoming : messages + incoming
        var byID: [String: ChatMessage] = [:]
        for message in source {
            byID[message.id] = message
        }
        messages = byID.values.sorted {
            if $0.createdAt != $1.createdAt {
                return $0.createdAt < $1.createdAt
            }
            return $0.id < $1.id
        }
    }

    private struct PendingReplyInput: Codable, Sendable {
        let questionID: String
        let text: String

        enum CodingKeys: String, CodingKey {
            case questionID = "questionId"
            case text
        }
    }
}
