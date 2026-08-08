import Foundation
import Observation

enum AppRoute: Equatable, Sendable {
    case restoring
    case welcome
    case calendarConnecting
    case profile
    case phone
    case analyzing
    case chat
    case softPaywall
    case fatal(AppErrorState)
}

struct AppErrorState: Equatable, Sendable {
    let backendErrorCode: String
    let localizedMessageKey: String
    let retryAllowed: Bool

    init(backendErrorCode: String, localizedMessageKey: String, retryAllowed: Bool) {
        self.backendErrorCode = backendErrorCode
        self.localizedMessageKey = localizedMessageKey
        self.retryAllowed = retryAllowed
    }

    init(error: Error) {
        switch error {
        case let APIError.server(statusCode):
            backendErrorCode = "http_\(statusCode)"
            localizedMessageKey = "error.server"
            retryAllowed = true
        case APIError.refreshRejected:
            backendErrorCode = "refresh_rejected"
            localizedMessageKey = "error.sessionExpired"
            retryAllowed = false
        case APIError.noSession, APIError.unauthorized:
            backendErrorCode = "unauthorized"
            localizedMessageKey = "error.sessionExpired"
            retryAllowed = false
        case APIError.invalidResponse, APIError.decodingFailed:
            backendErrorCode = "invalid_response"
            localizedMessageKey = "error.generic"
            retryAllowed = true
        case APIError.invalidURL:
            backendErrorCode = "invalid_url"
            localizedMessageKey = "error.generic"
            retryAllowed = false
        case APIError.transport:
            backendErrorCode = "transport_unavailable"
            localizedMessageKey = "error.network"
            retryAllowed = true
        default:
            backendErrorCode = "unknown_error"
            localizedMessageKey = "error.generic"
            retryAllowed = true
        }
    }
}

@MainActor
@Observable
final class AppViewModel {
    private let auth: AuthServicing
    private let profileService: ProfileServicing
    private let analysisService: AnalysisServicing
    let chatViewModel: ChatViewModel?
    let settingsViewModel: SettingsViewModel?
    let paywallViewModel: SoftPaywallViewModel?

    private(set) var route: AppRoute = .restoring
    private(set) var profile: UserProfile?
    private(set) var lastAnalysisStatus: AnalysisStatus?
    private(set) var phoneSkipped = false
    private(set) var phoneValidationError: String?
    private var profileChangedHandler: (@MainActor (UserProfile) async -> Void)?

    init(
        auth: AuthServicing,
        profile: ProfileServicing,
        analysis: AnalysisServicing,
        chat: ChatServicing? = nil,
        settings: SettingsViewModel? = nil,
        paywall: SoftPaywallViewModel? = nil
    ) {
        self.auth = auth
        profileService = profile
        analysisService = analysis
        if let chat {
            chatViewModel = ChatViewModel(service: chat)
        } else {
            chatViewModel = nil
        }
        settingsViewModel = settings
        paywallViewModel = paywall
    }

    var productLocale: ProductLocale {
        profile?.productLocale ?? .en
    }

    func setProfileChangedHandler(_ handler: (@MainActor (UserProfile) async -> Void)?) {
        profileChangedHandler = handler
    }

    func bindSettingsProfileHandler() {
        settingsViewModel?.setProfileChangedHandler { [weak self] profile in
            await self?.acceptProfile(profile)
        }
    }

    func acceptProfile(_ value: UserProfile) async {
        let localeChanged = profile?.productLocale != value.productLocale
        profile = value
        if localeChanged {
            await chatViewModel?.resetForLocaleChange()
        }
        await profileChangedHandler?(value)
    }

    func restoreSession() async {
        route = .restoring
        do {
            if try await auth.restoreSession() == nil {
                route = .welcome
            } else {
                route = .profile
            }
        } catch {
            present(error)
        }
    }

    func connectCalendar() async {
        route = .calendarConnecting
        do {
            _ = try await auth.connectCalendar()
            route = .profile
        } catch {
            present(error)
        }
    }

    func submitProfile(_ draft: ProfileDraft) async {
        route = .profile
        phoneValidationError = nil
        do {
            let updatedProfile = try await profileService.update(draft, idempotencyKey: UUID())
            await acceptProfile(updatedProfile)
            route = .phone
        } catch {
            present(error)
        }
    }

    func skipPhone() async {
        phoneSkipped = true
        await persistPhoneAndAnalyze(nil)
    }

    func submitPhone(_ value: String) async {
        phoneValidationError = nil
        guard E164PhoneValidator.isValid(value) else {
            phoneValidationError = "settings.phoneInvalid"
            route = .phone
            return
        }
        phoneSkipped = false
        await persistPhoneAndAnalyze(value)
    }

    func retryAnalysis() async {
        await runAnalysis()
    }

    func showSoftPaywall() {
        guard route == .chat, lastAnalysisStatus == .routeReady else { return }
        route = .softPaywall
    }

    func continueFree() {
        guard route == .softPaywall else { return }
        route = .chat
    }

    func cancelSoftPaywall() {
        continueFree()
    }

    func retryAfterFatal() async {
        guard case let .fatal(error) = route, error.retryAllowed else { return }
        await restoreSession()
    }

    private func runAnalysis() async {
        route = .analyzing
        do {
            let result = try await analysisService.analyzeNextCommitment(idempotencyKey: UUID())
            lastAnalysisStatus = result.status
            route = .chat
        } catch {
            present(error)
        }
    }

    private func persistPhoneAndAnalyze(_ phone: String?) async {
        guard let profile else {
            await runAnalysis()
            return
        }

        do {
            let updatedProfile = try await profileService.update(
                ProfileDraft(
                    name: profile.name,
                    home: profile.home.display,
                    productLocale: profile.productLocale,
                    phone: phone,
                    callsEnabled: false,
                    callLanguage: nil
                ),
                idempotencyKey: UUID()
            )
            await acceptProfile(updatedProfile)
            await runAnalysis()
        } catch {
            present(error)
        }
    }

    private func present(_ error: Error) {
        route = .fatal(AppErrorState(error: error))
    }
}
