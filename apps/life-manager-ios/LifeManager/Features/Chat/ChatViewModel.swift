import Foundation
import Observation

@MainActor
@Observable
final class ChatViewModel {
    private let service: ChatServicing
    private var fetchGeneration = 0
    private var answeredQuestionIDs = Set<String>()

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

    init(service: ChatServicing) {
        self.service = service
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
        await fetchFirstPage()
    }

    func refresh() async {
        guard !isLoading else { return }
        await fetchFirstPage()
    }

    func retry() async {
        await refresh()
    }

    func loadMore() async {
        guard
            !isLoadingMore,
            !isLoading,
            hasMore,
            let cursor = nextCursor
        else {
            return
        }

        isLoadingMore = true
        failure = nil
        let generation = fetchGeneration
        let existingAnchor = scrollAnchorID ?? messages.first?.id

        do {
            let page = try await service.fetch(after: cursor)
            guard generation == fetchGeneration else {
                isLoadingMore = false
                return
            }
            merge(page.messages, replacing: false)
            nextCursor = page.nextCursor
            hasMore = page.hasMore
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
        let value = (text ?? composerText).trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty, !isReplying else { return }

        let generation = fetchGeneration
        let questionID = question.id
        composerText = ""
        isReplying = true
        failure = nil
        staleReply = false

        do {
            let message = try await service.reply(
                questionID: questionID,
                text: value,
                idempotencyKey: UUID()
            )
            guard generation == fetchGeneration, openQuestion?.id == questionID else {
                staleReply = true
                isReplying = false
                return
            }
            answeredQuestionIDs.insert(questionID)
            merge([message], replacing: false)
        } catch {
            failure = AppErrorState(error: error)
        }

        isReplying = false
    }

    private func fetchFirstPage() async {
        isLoading = true
        failure = nil
        staleReply = false
        fetchGeneration &+= 1
        let generation = fetchGeneration

        do {
            let page = try await service.fetch(after: nil)
            guard generation == fetchGeneration else {
                isLoading = false
                return
            }
            merge(page.messages, replacing: true)
            nextCursor = page.nextCursor
            hasMore = page.hasMore
        } catch {
            if generation == fetchGeneration {
                failure = AppErrorState(error: error)
            }
        }

        isLoading = false
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
}
