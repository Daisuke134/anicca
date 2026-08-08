import SwiftUI

@MainActor
protocol ChatForegroundRefreshing: AnyObject {
    func refreshFromForeground() async
}

extension ChatViewModel: ChatForegroundRefreshing {
    func refreshFromForeground() async {
        await refresh()
    }
}

struct ChatView: View {
    @State private var viewModel: ChatViewModel
    @State private var selectedRouteMessage: ChatMessage?
    @State private var showingSettings = false

    init(viewModel: ChatViewModel) {
        _viewModel = State(initialValue: viewModel)
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
            Text("Settings")
                .font(.title2)
                .padding()
        }
        .task {
            await viewModel.loadInitial()
        }
    }

    private var header: some View {
        HStack {
            Text("Life Manager")
                .font(.headline)
                .accessibilityIdentifier("chat.list")
            Spacer()
            Button("Refresh") {
                Task { await viewModel.refresh() }
            }
            .accessibilityIdentifier("chat.refresh")
            Button("Settings") {
                showingSettings = true
            }
            .accessibilityIdentifier("chat.settings")
        }
        .padding(.horizontal)
        .padding(.vertical, 12)
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
                        Text("Your answer arrived after this chat changed. Review the latest question before replying.")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                            .accessibilityLabel("The answer was stale after the chat refreshed")
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
                ProgressView("Loading your chat")
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
        }
    }

    private func failureRow(_ failure: AppErrorState) -> some View {
        HStack(spacing: 12) {
            Text(failure.localizedMessageKey)
                .font(.footnote)
            if failure.retryAllowed {
                Button("Try again") {
                    Task { await viewModel.retry() }
                }
                .buttonStyle(.bordered)
            }
        }
        .accessibilityElement(children: .combine)
    }

    private var composer: some View {
        HStack(spacing: 8) {
            TextField("Answer the open question", text: $viewModel.composerText)
                .textFieldStyle(.roundedBorder)
                .accessibilityIdentifier("chat.composer")
            Button("Send") {
                Task { await viewModel.reply() }
            }
            .disabled(!viewModel.canReply || viewModel.composerText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            .accessibilityIdentifier("chat.send")
        }
        .padding()
    }
}
