import SwiftUI

struct RootView: View {
    let environment: AppEnvironment
    private let viewModel: AppViewModel?

    init(environment: AppEnvironment, viewModel: AppViewModel? = nil) {
        self.environment = environment
        self.viewModel = viewModel
    }

    var body: some View {
        if let viewModel {
            RouteSurface(viewModel: viewModel)
        } else {
            VStack {
                Text("Life Manager")
                    .font(.largeTitle)
                    .fontWeight(.semibold)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }
}

private struct RouteSurface: View {
    @State private var viewModel: AppViewModel
    @State private var profileName = ""
    @State private var profileHome = ""

    init(viewModel: AppViewModel) {
        _viewModel = State(initialValue: viewModel)
    }

    var body: some View {
        Group {
            switch viewModel.route {
            case .restoring:
                ProgressView("Restoring your Life Manager")
            case .welcome:
                welcomeView
            case .calendarConnecting:
                ProgressView("Connecting Calendar")
            case .profile:
                profileView
            case .phone:
                phoneView
            case .analyzing:
                ProgressView("Checking your next commitment")
                    .accessibilityIdentifier("analysis.phase")
            case .chat:
                if let chatViewModel = viewModel.chatViewModel {
                    ChatView(viewModel: chatViewModel)
                } else {
                    chatView
                }
            case .softPaywall:
                softPaywallView
            case let .fatal(error):
                fatalView(error)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .task {
            if viewModel.route == .restoring {
                await viewModel.restoreSession()
            }
        }
    }

    private var welcomeView: some View {
        VStack(spacing: 16) {
            Text("Life Manager")
                .font(.largeTitle)
                .fontWeight(.semibold)
            Text("Connect your Calendar to get one clear next step.")
                .multilineTextAlignment(.center)
            Button("Connect Calendar") {
                Task { await viewModel.connectCalendar() }
            }
            .accessibilityIdentifier("welcome.connectCalendar")
        }
        .padding()
    }

    private var profileView: some View {
        Form {
            Section("Your profile") {
                TextField("Name", text: $profileName)
                    .accessibilityIdentifier("profile.name")
                TextField("Home or usual starting point", text: $profileHome)
                    .accessibilityIdentifier("profile.home")
                Button("Continue") {
                    Task {
                        await viewModel.submitProfile(
                            ProfileDraft(name: profileName.isEmpty ? nil : profileName, home: profileHome.isEmpty ? nil : profileHome)
                        )
                    }
                }
                .accessibilityIdentifier("profile.continue")
            }
        }
        .frame(maxWidth: 520)
    }

    private var phoneView: some View {
        VStack(spacing: 16) {
            Text("Add a phone number for optional calls later.")
                .multilineTextAlignment(.center)
            Button("Skip for now") {
                Task { await viewModel.skipPhone() }
            }
            .accessibilityIdentifier("phone.skip")
        }
        .padding()
    }

    private var chatView: some View {
        VStack(spacing: 16) {
            Text("Life Manager")
                .font(.title)
            Text("Your next step is ready.")
            Button("See upgrade options") {
                viewModel.showSoftPaywall()
            }
        }
        .accessibilityIdentifier("chat.list")
        .padding()
    }

    private var softPaywallView: some View {
        SoftPaywallView {
            viewModel.continueFree()
        }
    }

    private func fatalView(_ error: AppErrorState) -> some View {
        VStack(spacing: 16) {
            Text(error.localizedMessageKey)
            if error.retryAllowed {
                Button("Try again") {
                    Task { await viewModel.retryAfterFatal() }
                }
                .accessibilityIdentifier("error.retry")
            }
        }
        .padding()
    }
}
