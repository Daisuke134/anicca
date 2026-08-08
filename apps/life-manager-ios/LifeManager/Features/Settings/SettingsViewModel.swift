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
    var phone = ""
    var callsEnabled = false
    var callLanguage: ProductLocale = .en

    init(
        profile: ProfileServicing,
        auth: AuthServicing,
        calls: CallServicing,
        account: AccountServicing
    ) {
        profileService = profile
        self.auth = auth
        callService = calls
        accountService = account
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
            apply(try await profileService.fetch())
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
        guard callsEnabled else {
            phoneValidationError = "settings.callsDisabled"
            return
        }
        guard phoneConfigured else {
            phoneValidationError = "settings.phoneRequired"
            return
        }

        do {
            callReceipt = try await callService.placeTestCall(idempotencyKey: UUID())
        } catch {
            failure = AppErrorState(error: error)
        }
    }

    func deleteAccount() async {
        failure = nil
        do {
            let receipt = try await accountService.deleteAccount(idempotencyKey: UUID())
            deletionReceipt = receipt
            try? await auth.signOut()
        } catch {
            failure = AppErrorState(error: error)
        }
    }

    func signOut() async {
        failure = nil
        do {
            try await auth.signOut()
        } catch {
            failure = AppErrorState(error: error)
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
        do {
            apply(try await profileService.update(draft, idempotencyKey: UUID()))
        } catch {
            failure = AppErrorState(error: error)
        }
    }

    private func apply(_ value: UserProfile) {
        profile = value
        name = value.name ?? ""
        home = value.home.display ?? ""
        productLocale = value.productLocale
        phone = value.phone.masked ?? ""
        callsEnabled = value.callsEnabled && value.phone.status == .configured
        callLanguage = value.callLanguage ?? .en
        calendarStatus = value.calendarStatus
    }
}
