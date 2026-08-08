import Foundation
import Observation

enum E164PhoneValidator {
    static func isValid(_ value: String) -> Bool {
        let scalars = Array(value)
        guard scalars.first == "+" else { return false }
        let digits = Array(scalars.dropFirst())
        guard (8...15).contains(digits.count), digits.first != "0" else { return false }
        return digits.allSatisfy { $0.isASCII && $0.isNumber }
    }
}

@MainActor
@Observable
final class SettingsViewModel {
    private let profileService: ProfileServicing
    private let auth: AuthServicing
    private let callService: CallServicing
    private let accountService: AccountServicing
    private let deviceService: DeviceServicing?
    private let retryStore: OperationRetryStoring
    private var profileChangedHandler: (@MainActor (UserProfile) async -> Void)?
    private var signedOutHandler: (@MainActor () async -> Void)?

    private(set) var profile: UserProfile?
    private(set) var calendarStatus: CalendarConnectionStatus = .disconnected
    private(set) var phoneValidationError: String?
    private(set) var callReceipt: CallReceipt?
    private(set) var deletionReceipt: AccountDeletionReceipt?
    private(set) var failure: AppErrorState?
    private(set) var isLoading = false

    var name = ""
    var home = ""
    var productLocale: ProductLocale = .en
    /// A server-confirmed, masked value for display only. Never reuse this as an edit payload.
    private(set) var phoneDisplay: String?
    /// A replacement E.164 value entered by the user. Empty means keep the existing number.
    var phone = ""
    var callsEnabled = false
    var callLanguage: ProductLocale = .en

    init(
        profile: ProfileServicing,
        auth: AuthServicing,
        calls: CallServicing,
        account: AccountServicing,
        device: DeviceServicing? = nil,
        retryStore: OperationRetryStoring = UserDefaultsOperationRetryStore()
    ) {
        profileService = profile
        self.auth = auth
        callService = calls
        accountService = account
        deviceService = device
        self.retryStore = retryStore
    }

    func setProfileChangedHandler(_ handler: (@MainActor (UserProfile) async -> Void)?) {
        profileChangedHandler = handler
    }

    func setSignedOutHandler(_ handler: (@MainActor () async -> Void)?) {
        signedOutHandler = handler
    }

    var phoneConfigured: Bool {
        profile?.phone.status == .configured || E164PhoneValidator.isValid(phone)
    }

    var callLanguageVisible: Bool {
        callsEnabled
    }

    func load() async {
        guard !isLoading else { return }
        isLoading = true
        failure = nil
        do {
            await apply(try await profileService.fetch())
        } catch {
            failure = AppErrorState(error: error)
        }
        isLoading = false
    }

    func saveProfile() async {
        guard validatePhone() else { return }
        let draft = makeDraft(callsEnabled: callsEnabled && phoneConfigured)
        await save(draft)
    }

    func setCallsEnabled(_ enabled: Bool) async {
        phoneValidationError = nil
        guard !enabled || phoneConfigured else {
            phoneValidationError = "settings.phoneRequired"
            callsEnabled = false
            return
        }
        let draft = makeDraft(callsEnabled: enabled)
        await save(draft)
    }

    func callMeNow() async {
        phoneValidationError = nil
        failure = nil
        guard callsEnabled else {
            phoneValidationError = "settings.callsDisabled"
            return
        }
        guard phoneConfigured else {
            phoneValidationError = "settings.phoneRequired"
            return
        }

        do {
            let operationKey = await operationKey(for: .call)
            callReceipt = try await callService.placeTestCall(idempotencyKey: operationKey)
            await retryStore.clear(.call)
        } catch {
            if !MutationRetryPolicy.shouldRetain(after: error) {
                await retryStore.clear(.call)
            }
            failure = AppErrorState(error: error)
        }
    }

    func deleteAccount() async {
        failure = nil
        let deletionOperationKey = await operationKey(for: .deletion)
        do {
            let deviceOperationKey = await operationKey(for: .deviceUnregistration)
            try await deviceService?.unregister(idempotencyKey: deviceOperationKey)
            await retryStore.clear(.deviceUnregistration)
            let receipt = try await accountService.deleteAccount(idempotencyKey: deletionOperationKey)
            await retryStore.clear(.deletion)
            deletionReceipt = receipt
            try? await auth.signOut()
            await signedOutHandler?()
        } catch {
            if !MutationRetryPolicy.shouldRetain(after: error) {
                await retryStore.clear(.deletion)
            }
            failure = AppErrorState(error: error)
        }
    }

    func signOut() async {
        failure = nil
        var firstError: Error?
        let deviceOperationKey = await operationKey(for: .deviceUnregistration)
        do {
            try await deviceService?.unregister(idempotencyKey: deviceOperationKey)
            await retryStore.clear(.deviceUnregistration)
        } catch {
            if !MutationRetryPolicy.shouldRetain(after: error) {
                await retryStore.clear(.deviceUnregistration)
            }
            firstError = error
        }
        do {
            try await auth.signOut()
        } catch {
            firstError = firstError ?? error
        }
        await signedOutHandler?()
        if let firstError {
            failure = AppErrorState(error: firstError)
        }
    }

    private func validatePhone() -> Bool {
        phoneValidationError = nil
        guard phone.isEmpty || E164PhoneValidator.isValid(phone) else {
            phoneValidationError = "settings.phoneInvalid"
            return false
        }
        return true
    }

    private func makeDraft(callsEnabled: Bool) -> ProfileDraft {
        ProfileDraft(
            name: name.isEmpty ? nil : name,
            home: home.isEmpty ? nil : home,
            productLocale: productLocale,
            phone: phone.isEmpty ? nil : phone,
            callsEnabled: callsEnabled,
            callLanguage: callsEnabled ? callLanguage : nil
        )
    }

    private func save(_ draft: ProfileDraft) async {
        failure = nil
        let operationKey = await operationKey(for: .profile, draft: draft)
        do {
            _ = try await profileService.update(draft, idempotencyKey: operationKey)
            await apply(try await profileService.fetch())
            await retryStore.clear(.profile)
        } catch {
            if !MutationRetryPolicy.shouldRetain(after: error) {
                await retryStore.clear(.profile)
            }
            failure = AppErrorState(error: error)
        }
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

    private func apply(_ value: UserProfile) async {
        profile = value
        name = value.name ?? ""
        home = value.home.display ?? ""
        productLocale = value.productLocale
        phoneDisplay = value.phone.masked
        phone = ""
        callsEnabled = value.callsEnabled && value.phone.status == .configured
        callLanguage = value.callLanguage ?? value.productLocale
        calendarStatus = value.calendarStatus
        await profileChangedHandler?(value)
    }
}
