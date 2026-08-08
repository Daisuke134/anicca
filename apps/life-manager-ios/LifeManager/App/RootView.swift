import SwiftUI

struct RootView: View {
    let environment: AppEnvironment
    private let viewModel: AppViewModel?
    private let onChatReady: (@MainActor () async -> Void)?

    init(
        environment: AppEnvironment,
        viewModel: AppViewModel? = nil,
        onChatReady: (@MainActor () async -> Void)? = nil
    ) {
        self.environment = environment
        self.viewModel = viewModel
        self.onChatReady = onChatReady
    }

    var body: some View {
        if let viewModel {
            RouteSurface(viewModel: viewModel, onChatReady: onChatReady)
        } else {
            VStack(spacing: 12) {
                Text("app.name")
                    .font(.largeTitle)
                    .fontWeight(.semibold)
                Text("welcome.promise")
                    .multilineTextAlignment(.center)
            }
            .padding()
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }
}

private struct RouteSurface: View {
    @State private var viewModel: AppViewModel
    private let onChatReady: (@MainActor () async -> Void)?
    @State private var profileName = ""
    @State private var profileHome = ""
    @State private var profileLocale: ProductLocale
    @State private var phoneNumber = ""

    init(
        viewModel: AppViewModel,
        onChatReady: (@MainActor () async -> Void)? = nil
    ) {
        _viewModel = State(initialValue: viewModel)
        self.onChatReady = onChatReady
        _profileLocale = State(initialValue: Self.preferredProductLocale)
    }

    var body: some View {
        Group {
            switch viewModel.route {
            case .restoring:
                ProgressView("onboarding.restoring")
            case .welcome:
                welcomeView
            case .calendarConnecting:
                ProgressView("onboarding.connectingCalendar")
            case .profile:
                profileView
            case .phone:
                phoneView
            case .analyzing:
                ProgressView("onboarding.analyzing")
                    .accessibilityIdentifier("analysis.phase")
            case .chat:
                Group {
                    if let chatViewModel = viewModel.chatViewModel {
                        ChatView(
                            viewModel: chatViewModel,
                            settingsViewModel: viewModel.settingsViewModel,
                            paywallViewModel: viewModel.paywallViewModel,
                            onShowPaywall: {
                                Task { await viewModel.presentSoftPaywallIfEligible() }
                            },
                            onUsefulRouteCard: {
                                await viewModel.presentSoftPaywallIfEligible()
                            }
                        )
                    } else {
                        chatView
                    }
                }
                .task {
                    await onChatReady?()
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
        .environment(\.locale, viewModel.productLocale.swiftUILocale)
    }

    private var welcomeView: some View {
        VStack(spacing: 16) {
            Text("app.name")
                .font(.largeTitle)
                .fontWeight(.semibold)
            Text("welcome.promise")
                .multilineTextAlignment(.center)
            Button("welcome.connectCalendar") {
                Task { await viewModel.connectCalendar() }
            }
            .accessibilityIdentifier("welcome.connectCalendar")
        }
        .padding()
    }

    private var profileView: some View {
        Form {
            Section("profile.title") {
                TextField("profile.name", text: $profileName)
                    .accessibilityIdentifier("profile.name")
                TextField("profile.home", text: $profileHome)
                    .accessibilityIdentifier("profile.home")
                Button("profile.continue") {
                    Task {
                        await viewModel.submitProfile(
                            ProfileDraft(
                                name: profileName.isEmpty ? nil : profileName,
                                home: profileHome.isEmpty ? nil : profileHome,
                                productLocale: profileLocale
                            )
                        )
                    }
                }
                .accessibilityIdentifier("profile.continue")
            }
            Section("settings.productLanguage") {
                Picker("settings.productLanguage", selection: $profileLocale) {
                    Text("settings.english")
                        .tag(ProductLocale.en)
                        .accessibilityIdentifier("profile.locale.en")
                    Text("settings.japanese")
                        .tag(ProductLocale.ja)
                        .accessibilityIdentifier("profile.locale.ja")
                }
                .accessibilityIdentifier("profile.productLocale")
            }
        }
        .frame(maxWidth: 520)
    }

    private var phoneView: some View {
        VStack(spacing: 16) {
            Text("phone.prompt")
                .multilineTextAlignment(.center)
            TextField("phone.number", text: $phoneNumber)
                .keyboardType(.phonePad)
                .textFieldStyle(.roundedBorder)
                .accessibilityIdentifier("phone.number")
            if let phoneValidationError = viewModel.phoneValidationError {
                Text(LocalizedStringKey(phoneValidationError))
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("phone.error")
            }
            Button("phone.add") {
                Task { await viewModel.submitPhone(phoneNumber) }
            }
            .buttonStyle(.borderedProminent)
            .accessibilityIdentifier("phone.add")
            Button("phone.skip") {
                Task { await viewModel.skipPhone() }
            }
            .accessibilityIdentifier("phone.skip")
        }
        .padding()
    }

    private static var preferredProductLocale: ProductLocale {
        guard let language = Locale.preferredLanguages.first?.lowercased(), language.hasPrefix("ja") else {
            return .en
        }
        return .ja
    }

    private var chatView: some View {
        VStack(spacing: 16) {
            Text("app.name")
                .font(.title)
            Text("analysis.checking")
            Button("paywall.upgrade") {
                viewModel.showSoftPaywall()
            }
        }
        .accessibilityIdentifier("chat.list")
        .padding()
    }

    private var softPaywallView: some View {
        SoftPaywallView(viewModel: viewModel.paywallViewModel) {
            viewModel.continueFree()
        }
    }

    private func fatalView(_ error: AppErrorState) -> some View {
        VStack(spacing: 16) {
            Text(LocalizedStringKey(error.localizedMessageKey))
            if error.retryAllowed {
                Button("chat.tryAgain") {
                    Task { await viewModel.retryAfterFatal() }
                }
                .accessibilityIdentifier("error.retry")
            }
        }
        .padding()
    }
}
