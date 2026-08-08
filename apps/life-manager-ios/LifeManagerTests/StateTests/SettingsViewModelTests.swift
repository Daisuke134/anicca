import Foundation
import XCTest
@testable import LifeManager

@MainActor
final class SettingsViewModelTests: XCTestCase {
    func testE164ValidationRejectsAmbiguousOrOverlongPhoneNumbers() {
        XCTAssertTrue(E164PhoneValidator.isValid("+14155552671"))
        XCTAssertTrue(E164PhoneValidator.isValid("+819012345678"))
        XCTAssertFalse(E164PhoneValidator.isValid("09012345678"))
        XCTAssertFalse(E164PhoneValidator.isValid("+1 415 555 2671"))
        XCTAssertFalse(E164PhoneValidator.isValid("+1234567"))
        XCTAssertFalse(E164PhoneValidator.isValid("+1234567890123456"))
    }

    func testLoadProjectsCalendarProfilePhoneAndConditionalCallLanguage() async {
        let profile = SettingsFixtures.profile(callsEnabled: true, phone: .configured("+81••••••5678"), callLanguage: .ja)
        let viewModel = makeViewModel(profile: profile)

        await viewModel.load()

        XCTAssertEqual(viewModel.calendarStatus, .connected)
        XCTAssertEqual(viewModel.name, "Alex")
        XCTAssertEqual(viewModel.home, "Home")
        XCTAssertTrue(viewModel.phoneConfigured)
        XCTAssertTrue(viewModel.callsEnabled)
        XCTAssertEqual(viewModel.callLanguage, .ja)
        XCTAssertTrue(viewModel.callLanguageVisible)
    }

    func testSavedProductLocaleNotifiesTheAppAfterServerConfirmation() async {
        let profileService = SettingsProfileTestService(profile: SettingsFixtures.profile(callsEnabled: false, phone: .missing, callLanguage: nil))
        let viewModel = makeViewModel(profileService: profileService)
        var changedProfiles: [UserProfile] = []
        viewModel.setProfileChangedHandler { profile in
            changedProfiles.append(profile)
        }

        await viewModel.load()
        viewModel.productLocale = .ja
        await viewModel.saveProfile()

        XCTAssertEqual(changedProfiles.map(\.productLocale), [.en, .ja])
    }

    func testProductLocaleMapsToSwiftUILocaleIdentifier() {
        XCTAssertEqual(ProductLocale.en.swiftUILocale.identifier, "en")
        XCTAssertEqual(ProductLocale.ja.swiftUILocale.identifier, "ja")
    }

    func testSavingPhoneDoesNotEnableCallsAndInvalidPhoneNeverSendsMutation() async {
        let profile = SettingsFixtures.profile(callsEnabled: false, phone: .missing, callLanguage: nil)
        let profileService = SettingsProfileTestService(profile: profile)
        let viewModel = makeViewModel(profile: profile, profileService: profileService)

        await viewModel.load()
        viewModel.phone = "+14155552671"
        await viewModel.saveProfile()

        XCTAssertNil(viewModel.phoneValidationError)
        XCTAssertFalse(viewModel.callsEnabled)
        let firstDraft = await profileService.drafts().last
        XCTAssertEqual(firstDraft?.phone, "+14155552671")
        XCTAssertEqual(firstDraft?.callsEnabled, false)

        viewModel.phone = "not-a-phone"
        await viewModel.saveProfile()

        XCTAssertEqual(viewModel.phoneValidationError, "settings.phoneInvalid")
        let draftsAfterInvalid = await profileService.drafts()
        XCTAssertEqual(draftsAfterInvalid.count, 1)
    }

    func testCallsToggleRequiresConfiguredPhoneAndCallLanguageIsConditional() async {
        let profile = SettingsFixtures.profile(callsEnabled: false, phone: .missing, callLanguage: nil)
        let profileService = SettingsProfileTestService(profile: profile)
        let viewModel = makeViewModel(profile: profile, profileService: profileService)
        await viewModel.load()

        await viewModel.setCallsEnabled(true)
        XCTAssertEqual(viewModel.phoneValidationError, "settings.phoneRequired")
        XCTAssertFalse(viewModel.callsEnabled)
        let draftsBeforePhone = await profileService.drafts()
        XCTAssertEqual(draftsBeforePhone.count, 0)

        viewModel.phone = "+14155552671"
        await viewModel.saveProfile()
        viewModel.callLanguage = .ja
        await viewModel.setCallsEnabled(true)

        XCTAssertTrue(viewModel.callsEnabled)
        XCTAssertTrue(viewModel.callLanguageVisible)
        let enabledDraft = await profileService.drafts().last
        XCTAssertEqual(enabledDraft?.callLanguage, .ja)

        await viewModel.setCallsEnabled(false)
        XCTAssertFalse(viewModel.callsEnabled)
        XCTAssertFalse(viewModel.callLanguageVisible)
        let disabledDraft = await profileService.drafts().last
        XCTAssertNil(disabledDraft?.callLanguage)
    }

    func testCallMeNowRequiresExplicitEnabledToggleAndSurfacesServerReceipt() async {
        let callService = SettingsCallTestService(receipt: CallReceipt(
            requestID: "call-request-1",
            status: .accepted,
            cooldownSeconds: 120,
            dailyRemaining: 2,
            message: "Call queued"
        ))
        let profile = SettingsFixtures.profile(callsEnabled: true, phone: .configured("+81••••••5678"), callLanguage: .en)
        let viewModel = makeViewModel(profile: profile, callService: callService)
        await viewModel.load()

        await viewModel.callMeNow()

        XCTAssertEqual(viewModel.callReceipt?.requestID, "call-request-1")
        XCTAssertEqual(viewModel.callReceipt?.cooldownSeconds, 120)
        XCTAssertEqual(viewModel.callReceipt?.dailyRemaining, 2)
        let acceptedRequestCount = await callService.requestCount()
        XCTAssertEqual(acceptedRequestCount, 1)
    }

    func testCallMeNowDoesNotCallServerWhenCallsAreDisabled() async {
        let callService = SettingsCallTestService(receipt: nil)
        let profile = SettingsFixtures.profile(callsEnabled: false, phone: .configured("+81••••••5678"), callLanguage: nil)
        let viewModel = makeViewModel(profile: profile, callService: callService)
        await viewModel.load()

        await viewModel.callMeNow()

        XCTAssertEqual(viewModel.phoneValidationError, "settings.callsDisabled")
        let disabledRequestCount = await callService.requestCount()
        XCTAssertEqual(disabledRequestCount, 0)
    }

    func testDeletionDisplaysBackendReceiptThenClearsLocalSession() async {
        let receipt = AccountDeletionReceipt(
            receiptID: "deletion-1",
            deletedAt: Date.iso8601("2026-08-10T08:20:00.000Z"),
            sessionsRevoked: true,
            providerConnectionsRevoked: true
        )
        let auth = SettingsAuthTestService()
        let account = SettingsAccountTestService(receipt: receipt)
        let viewModel = makeViewModel(auth: auth, accountService: account)
        await viewModel.load()

        await viewModel.deleteAccount()

        XCTAssertEqual(viewModel.deletionReceipt, receipt)
        let deletionRequestCount = await account.requestCount()
        let signOutCount = await auth.signOutCount()
        XCTAssertEqual(deletionRequestCount, 1)
        XCTAssertEqual(signOutCount, 1)
    }

    private func makeViewModel(
        profile: UserProfile = SettingsFixtures.profile(callsEnabled: false, phone: .missing, callLanguage: nil),
        profileService: SettingsProfileTestService? = nil,
        auth: SettingsAuthTestService = SettingsAuthTestService(),
        callService: SettingsCallTestService = SettingsCallTestService(receipt: nil),
        accountService: SettingsAccountTestService = SettingsAccountTestService(receipt: nil)
    ) -> SettingsViewModel {
        SettingsViewModel(
            profile: profileService ?? SettingsProfileTestService(profile: profile),
            auth: auth,
            calls: callService,
            account: accountService
        )
    }
}

private enum SettingsFixtures {
    static func profile(
        callsEnabled: Bool,
        phone: PhoneSettings,
        callLanguage: ProductLocale?
    ) -> UserProfile {
        UserProfile(
            id: "user-settings-1",
            name: "Alex",
            home: HomeAddress(status: .ready, display: "Home"),
            productLocale: .en,
            timezone: "America/Los_Angeles",
            phone: phone,
            callsEnabled: callsEnabled,
            callLanguage: callLanguage,
            calendarStatus: .connected,
            offerStatus: .available
        )
    }
}

private actor SettingsProfileTestService: ProfileServicing {
    private var profileValue: UserProfile
    private var recordedDrafts: [ProfileDraft] = []

    init(profile: UserProfile) { profileValue = profile }

    func fetch() async throws -> UserProfile { profileValue }

    func update(_ draft: ProfileDraft, idempotencyKey: UUID) async throws -> UserProfile {
        recordedDrafts.append(draft)
        profileValue = UserProfile(
            id: profileValue.id,
            name: draft.name,
            home: HomeAddress(status: draft.home == nil ? .missing : .ready, display: draft.home),
            productLocale: draft.productLocale,
            timezone: profileValue.timezone,
            phone: draft.phone.map { .configured($0) } ?? .missing,
            callsEnabled: draft.callsEnabled,
            callLanguage: draft.callLanguage,
            calendarStatus: profileValue.calendarStatus,
            offerStatus: profileValue.offerStatus
        )
        return profileValue
    }

    func drafts() -> [ProfileDraft] { recordedDrafts }
}

private actor SettingsCallTestService: CallServicing {
    private let receipt: CallReceipt?
    private var requests = 0
    init(receipt: CallReceipt?) { self.receipt = receipt }

    func placeTestCall(idempotencyKey: UUID) async throws -> CallReceipt {
        requests += 1
        guard let receipt else { throw APIError.server(statusCode: 503) }
        return receipt
    }

    func requestCount() -> Int { requests }
}

private actor SettingsAccountTestService: AccountServicing {
    private let receipt: AccountDeletionReceipt?
    private var requests = 0
    init(receipt: AccountDeletionReceipt?) { self.receipt = receipt }

    func deleteAccount(idempotencyKey: UUID) async throws -> AccountDeletionReceipt {
        requests += 1
        guard let receipt else { throw APIError.server(statusCode: 503) }
        return receipt
    }

    func requestCount() -> Int { requests }
}

private actor SettingsAuthTestService: AuthServicing {
    private var signOuts = 0
    func restoreSession() async throws -> Session? { nil }
    func connectCalendar() async throws -> Session { fatalError("not used") }
    func refresh(_ session: Session) async throws -> Session { session }
    func signOut() async throws { signOuts += 1 }
    func signOutCount() -> Int { signOuts }
}
