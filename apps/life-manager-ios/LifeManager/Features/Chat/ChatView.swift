import SwiftUI

@MainActor
protocol ChatForegroundRefreshing: AnyObject {
    func refreshFromForeground() async
}

extension ChatViewModel: ChatForegroundRefreshing {
    func refreshFromForeground() async {
        await syncFromForeground()
    }
}

struct ChatView: View {
    @State private var viewModel: ChatViewModel
    @Environment(\.scenePhase) private var scenePhase
    private let settingsViewModel: SettingsViewModel?
    private let paywallViewModel: SoftPaywallViewModel?
    private let pushRouter: PushNotificationRouter
    private let onShowPaywall: (() -> Void)?
    private let onUsefulRouteCard: (@MainActor () async -> Void)?
    @State private var selectedRouteMessage: ChatMessage?
    @State private var showingSettings = false

    @MainActor
    init(
        viewModel: ChatViewModel,
        settingsViewModel: SettingsViewModel? = nil,
        paywallViewModel: SoftPaywallViewModel? = nil,
        pushRouter: PushNotificationRouter? = nil,
        onShowPaywall: (() -> Void)? = nil,
        onUsefulRouteCard: (@MainActor () async -> Void)? = nil
    ) {
        _viewModel = State(initialValue: viewModel)
        self.settingsViewModel = settingsViewModel
        self.paywallViewModel = paywallViewModel
        self.pushRouter = pushRouter ?? .shared
        self.onShowPaywall = onShowPaywall
        self.onUsefulRouteCard = onUsefulRouteCard
    }

    var body: some View {
        VStack(spacing: 0) {
            header
            messageList
            if viewModel.composerVisible {
                composer
            }
        }
        .sheet(item: $selectedRouteMessage) { message in
            if let presentation = RoutePresentation.detail(for: message) {
                RouteDetailSheet(presentation: presentation)
            }
        }
        .sheet(isPresented: $showingSettings) {
            if let settingsViewModel {
                SettingsView(viewModel: settingsViewModel, paywallViewModel: paywallViewModel)
            } else {
                Text("settings.title")
                    .font(.title2)
                    .padding()
            }
        }
        .task {
            await viewModel.loadInitial()
            await Task.yield()
            await onUsefulRouteCard?()
        }
        .onChange(of: scenePhase) { _, phase in
            guard phase == .active else { return }
            Task { await viewModel.refreshFromForeground() }
        }
        .onAppear {
            pushRouter.setHandler { destination in
                Task { await viewModel.syncFromPush(targetMessageID: destination.messageID) }
            }
        }
        .onDisappear {
            pushRouter.clearHandler()
        }
    }

    private var header: some View {
        HStack {
            Text("app.name")
                .font(.headline)
                .accessibilityIdentifier("chat.list")
            Spacer()
            Button("chat.refresh") {
                Task { await viewModel.refresh() }
            }
            .accessibilityIdentifier("chat.refresh")
            Button("chat.settings") {
                showingSettings = true
            }
            .accessibilityIdentifier("chat.settings")
            if hasUsefulRoute, let onShowPaywall {
                Button("paywall.upgrade", action: onShowPaywall)
                    .accessibilityIdentifier("chat.upgrade")
            }
        }
        .padding(.horizontal)
        .padding(.vertical, 12)
    }

    private var hasUsefulRoute: Bool {
        viewModel.messages.contains { message in
            message.type == .route && RoutePresentation.card(for: message) != nil
        }
    }

    private var messageList: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 12) {
                    ForEach(viewModel.messages) { message in
                        messageRow(message)
                            .id(message.id)
                    }

                    if let failure = viewModel.failure {
                        failureRow(failure)
                    }

                    if viewModel.staleReply {
                        Text("chat.staleReply")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                            .accessibilityLabel(LocalizedStringKey("chat.staleReplyAccessibility"))
                    }
                }
                .padding()
            }
            .refreshable {
                await viewModel.refresh()
            }
            .onChange(of: viewModel.scrollAnchorID) { _, anchorID in
                guard let anchorID else { return }
                withAnimation { proxy.scrollTo(anchorID, anchor: .top) }
            }
        }
        .overlay {
            if viewModel.isLoading && viewModel.messages.isEmpty {
                ProgressView("chat.loading")
            }
        }
    }

    @ViewBuilder
    private func messageRow(_ message: ChatMessage) -> some View {
        if message.type == .route, RoutePresentation.card(for: message) != nil {
            RouteCardView(message: message) {
                selectedRouteMessage = message
            }
        } else {
            VStack(alignment: .leading, spacing: 6) {
                Text(message.text)
                    .font(.body)
                if let question = message.question, message.type == .question {
                    Text(question.prompt)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                ForEach(message.actions) { action in
                    if action.id == "refresh" {
                        Button(action.label) {
                            Task { await viewModel.refresh() }
                        }
                    }
                }
            }
            .padding()
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 14))
            .accessibilityIdentifier("chat.message.\(message.id)")
        }
    }

    private func failureRow(_ failure: AppErrorState) -> some View {
        HStack(spacing: 12) {
            Text(LocalizedStringKey(failure.localizedMessageKey))
                .font(.footnote)
            if failure.retryAllowed {
                Button("chat.tryAgain") {
                    Task { await viewModel.retry() }
                }
                .buttonStyle(.bordered)
            }
        }
        .accessibilityElement(children: .combine)
    }

    private var composer: some View {
        HStack(spacing: 8) {
            TextField("chat.answerOpenQuestion", text: $viewModel.composerText)
                .textFieldStyle(.roundedBorder)
                .accessibilityIdentifier("chat.composer")
            Button("chat.send") {
                Task { await viewModel.reply() }
            }
            .disabled(!viewModel.canReply || viewModel.composerText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            .accessibilityIdentifier("chat.send")
        }
        .padding()
    }
}
