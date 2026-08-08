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
    private let retryStore: OperationRetryStoring
    let chatViewModel: ChatViewModel?
    let settingsViewModel: SettingsViewModel?
    let paywallViewModel: SoftPaywallViewModel?

    private(set) var route: AppRoute = .restoring
    private(set) var profile: UserProfile?
    private(set) var lastAnalysisStatus: AnalysisStatus?
    private(set) var lastAnalysisReceipt: AnalysisResult?
    private(set) var phoneSkipped = false
    private(set) var phoneValidationError: String?
    private var profileChangedHandler: (@MainActor (UserProfile) async -> Void)?
    private var hasPresentedSoftPaywall = false

    init(
        auth: AuthServicing,
        profile: ProfileServicing,
        analysis: AnalysisServicing,
        chat: ChatServicing? = nil,
        settings: SettingsViewModel? = nil,
        paywall: SoftPaywallViewModel? = nil,
        retryStore: OperationRetryStoring = UserDefaultsOperationRetryStore()
    ) {
        self.auth = auth
        profileService = profile
        analysisService = analysis
        self.retryStore = retryStore
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
        settingsViewModel?.setSignedOutHandler { [weak self] in
            await self?.handleSignedOut()
        }
    }

    func acceptProfile(_ value: UserProfile) async {
        let localeChanged = profile.map { $0.productLocale != value.productLocale } ?? false
        profile = value
        if localeChanged {
            await chatViewModel?.resetForLocaleChange()
        }
        await profileChangedHandler?(value)
    }

    private func handleSignedOut() async {
        route = .welcome
        profile = nil
        lastAnalysisStatus = nil
        lastAnalysisReceipt = nil
        await chatViewModel?.clearProjection()
    }

    func restoreSession() async {
        route = .restoring
        do {
            guard try await auth.restoreSession() != nil else {
                route = .welcome
                return
            }

            let restoredProfile = try await profileService.fetch()
            await acceptProfile(restoredProfile)
            guard restoredProfile.calendarStatus == .connected else {
                route = .welcome
                return
            }
            guard restoredProfile.name != nil, restoredProfile.home.status == .ready else {
                route = .profile
                return
            }
            if restoredProfile.analysisStatus == .idle && restoredProfile.phone.status == .missing {
                route = .phone
                return
            }

            if let status = AnalysisStatus(rawValue: restoredProfile.analysisStatus.rawValue) {
                lastAnalysisStatus = status
            }
            await chatViewModel?.loadInitial()
            route = .chat
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
            let updatedProfile = try await profileService.update(
                draft,
                idempotencyKey: await operationKey(for: .profile, draft: draft)
            )
            await retryStore.clear(.profile)
            await acceptProfile(updatedProfile)
            route = .phone
        } catch {
            if !MutationRetryPolicy.shouldRetain(after: error) {
                await retryStore.clear(.profile)
            }
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
        guard route == .chat, lastAnalysisStatus == .routeReady, !hasPresentedSoftPaywall else { return }
        hasPresentedSoftPaywall = true
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
        let operationKey = await operationKey(for: .analysis)
        do {
            let result = try await analysisService.analyzeNextCommitment(idempotencyKey: operationKey)
            await retryStore.clear(.analysis)
            lastAnalysisReceipt = result
            lastAnalysisStatus = result.status
            route = .chat
        } catch {
            if !MutationRetryPolicy.shouldRetain(after: error) {
                await retryStore.clear(.analysis)
            }
            present(error)
        }
    }

    private func persistPhoneAndAnalyze(_ phone: String?) async {
        guard let profile else {
            await runAnalysis()
            return
        }

        do {
            let draft = ProfileDraft(
                name: profile.name,
                home: profile.home.display,
                productLocale: profile.productLocale,
                phone: phone,
                callsEnabled: false,
                callLanguage: nil
            )
            let updatedProfile = try await profileService.update(
                draft,
                idempotencyKey: await operationKey(for: .profile, draft: draft)
            )
            await retryStore.clear(.profile)
            await acceptProfile(updatedProfile)
            await runAnalysis()
        } catch {
            if !MutationRetryPolicy.shouldRetain(after: error) {
                await retryStore.clear(.profile)
            }
            present(error)
        }
    }

    private func present(_ error: Error) {
        route = .fatal(AppErrorState(error: error))
    }

    private func operationKey(for operation: RetryOperation, draft: ProfileDraft? = nil) async -> UUID {
        if let pending = await retryStore.pending(for: operation) {
            if let draft,
               let data = pending.input,
               let persistedDraft = try? JSONDecoder.lifeManager.decode(ProfileDraft.self, from: data),
               persistedDraft != draft {
                let key = UUID()
                let input = try? JSONEncoder.lifeManager.encode(draft)
                await retryStore.save(operation, value: PendingOperation(idempotencyKey: key, input: input))
                return key
            }
            return pending.idempotencyKey
        }

        let key = UUID()
        let input = draft.flatMap { try? JSONEncoder.lifeManager.encode($0) }
        await retryStore.save(operation, value: PendingOperation(idempotencyKey: key, input: input))
        return key
    }
}
