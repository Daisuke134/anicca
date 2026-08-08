import Foundation
import XCTest
@testable import LifeManager

@MainActor
final class AppDelegatePushTests: XCTestCase {
    func testDeniedPermissionDoesNotRegisterForRemoteNotifications() async throws {
        let permission = PushPermissionStub(status: .denied, requestResult: true)
        let registrar = RemoteNotificationRegistrarStub()
        let appDelegate = LifeManagerAppDelegate(
            permissionService: permission,
            registrar: registrar,
            pushRouter: PushNotificationRouter(),
            environment: .sandbox
        )

        let granted = try await appDelegate.requestAuthorizationAndRegisterIfNeeded()

        XCTAssertFalse(granted)
        XCTAssertEqual(permission.requestCount, 0)
        XCTAssertEqual(registrar.registerCount, 0)
    }

    func testNotDeterminedPermissionRegistersOnlyAfterAuthorization() async throws {
        let permission = PushPermissionStub(status: .notDetermined, requestResult: true)
        let registrar = RemoteNotificationRegistrarStub()
        let appDelegate = LifeManagerAppDelegate(
            permissionService: permission,
            registrar: registrar,
            pushRouter: PushNotificationRouter(),
            environment: .sandbox
        )

        let granted = try await appDelegate.requestAuthorizationAndRegisterIfNeeded()

        XCTAssertTrue(granted)
        XCTAssertEqual(permission.requestCount, 1)
        XCTAssertEqual(registrar.registerCount, 1)
    }

    func testAuthorizedPermissionRegistersWithoutRequestingAgain() async throws {
        let permission = PushPermissionStub(status: .authorized, requestResult: false)
        let registrar = RemoteNotificationRegistrarStub()
        let appDelegate = LifeManagerAppDelegate(
            permissionService: permission,
            registrar: registrar,
            pushRouter: PushNotificationRouter(),
            environment: .production
        )

        let granted = try await appDelegate.requestAuthorizationAndRegisterIfNeeded()

        XCTAssertTrue(granted)
        XCTAssertEqual(permission.requestCount, 0)
        XCTAssertEqual(registrar.registerCount, 1)
    }

    func testRemoteTokenRegistersOnlyAfterPermissionGateAndComposition() async throws {
        let permission = PushPermissionStub(status: .authorized, requestResult: false)
        let registrar = RemoteNotificationRegistrarStub()
        let recorder = PushDeviceServiceStub()
        let appDelegate = LifeManagerAppDelegate(
            permissionService: permission,
            registrar: registrar,
            pushRouter: PushNotificationRouter(),
            environment: .production
        )
        appDelegate.configure(
            deviceService: recorder,
            locale: .ja,
            timezone: "Asia/Tokyo"
        )
        _ = try await appDelegate.requestAuthorizationAndRegisterIfNeeded()

        let token = Data(repeating: 0xAB, count: 32)
        await appDelegate.registerDeviceToken(token)

        let registration = recorder.registration
        XCTAssertEqual(registration?.token, token)
        XCTAssertEqual(registration?.environment, .production)
        XCTAssertEqual(registration?.locale, .ja)
        XCTAssertEqual(registration?.timezone, "Asia/Tokyo")
    }

    func testLocaleChangeReregistersExistingTokenWithUpdatedLocale() async throws {
        let permission = PushPermissionStub(status: .authorized, requestResult: false)
        let recorder = PushDeviceServiceStub()
        let appDelegate = LifeManagerAppDelegate(
            permissionService: permission,
            registrar: RemoteNotificationRegistrarStub(),
            pushRouter: PushNotificationRouter(),
            environment: .production
        )
        appDelegate.configure(deviceService: recorder, locale: .en, timezone: "America/Los_Angeles")
        _ = try await appDelegate.requestAuthorizationAndRegisterIfNeeded()
        await appDelegate.registerDeviceToken(Data(repeating: 0xAB, count: 32))

        await appDelegate.updateDeviceLocale(.ja, timezone: "Asia/Tokyo")

        XCTAssertEqual(recorder.registrationCount, 2)
        XCTAssertEqual(recorder.registration?.locale, .ja)
        XCTAssertEqual(recorder.registration?.timezone, "Asia/Tokyo")
    }

    func testAmbiguousAPNsRegistrationReplaysOldBodyThenFollowsUpWithCurrentLocale() async throws {
        let store = TestOperationRetryStore()
        let firstRecorder = PushDeviceServiceStub(failRegistrationOnce: true)
        let firstDelegate = LifeManagerAppDelegate(
            permissionService: PushPermissionStub(status: .authorized, requestResult: false),
            registrar: RemoteNotificationRegistrarStub(),
            pushRouter: PushNotificationRouter(),
            environment: .production,
            retryStore: store
        )
        firstDelegate.configure(deviceService: firstRecorder, locale: .ja, timezone: "Asia/Tokyo")
        _ = try await firstDelegate.requestAuthorizationAndRegisterIfNeeded()
        await firstDelegate.registerDeviceToken(Data(repeating: 0xAB, count: 32))

        let pendingValue = await store.pending(for: .deviceRegistration)
        let pending = try XCTUnwrap(pendingValue)

        let secondRecorder = PushDeviceServiceStub()
        let secondDelegate = LifeManagerAppDelegate(
            permissionService: PushPermissionStub(status: .authorized, requestResult: false),
            registrar: RemoteNotificationRegistrarStub(),
            pushRouter: PushNotificationRouter(),
            environment: .production,
            retryStore: store
        )
        secondDelegate.configure(deviceService: secondRecorder, locale: .en, timezone: "UTC")
        _ = try await secondDelegate.requestAuthorizationAndRegisterIfNeeded()
        await secondDelegate.retryDeviceRegistration()

        for _ in 0..<20 where secondRecorder.registrations.count < 2 {
            await Task.yield()
        }

        let registrations = secondRecorder.registrations
        XCTAssertEqual(registrations.count, 2)
        XCTAssertEqual(registrations[0].token, Data(repeating: 0xAB, count: 32))
        XCTAssertEqual(registrations[0].locale, .ja)
        XCTAssertEqual(registrations[0].timezone, "Asia/Tokyo")
        XCTAssertEqual(registrations[0].idempotencyKey, pending.idempotencyKey)
        XCTAssertEqual(registrations[1].token, Data(repeating: 0xAB, count: 32))
        XCTAssertEqual(registrations[1].locale, .en)
        XCTAssertEqual(registrations[1].timezone, "UTC")
        XCTAssertNotEqual(registrations[1].idempotencyKey, pending.idempotencyKey)
        let pendingAfterSuccess = await store.pending(for: .deviceRegistration)
        XCTAssertNil(pendingAfterSuccess)
    }

    func testAmbiguousAPNsUnregistrationReusesDurableKeyUntilSuccess() async throws {
        let store = TestOperationRetryStore()
        let recorder = PushDeviceServiceStub(failUnregistrationOnce: true)
        let appDelegate = LifeManagerAppDelegate(
            permissionService: PushPermissionStub(status: .authorized, requestResult: false),
            registrar: RemoteNotificationRegistrarStub(),
            pushRouter: PushNotificationRouter(),
            environment: .production,
            retryStore: store
        )
        appDelegate.configure(deviceService: recorder, locale: .en, timezone: "UTC")

        try? await appDelegate.unregisterDevice()
        let pendingValue = await store.pending(for: .deviceUnregistration)
        let pending = try XCTUnwrap(pendingValue)

        try await appDelegate.unregisterDevice()

        XCTAssertEqual(recorder.unregisterKeys, [pending.idempotencyKey, pending.idempotencyKey])
        let pendingAfterSuccess = await store.pending(for: .deviceUnregistration)
        XCTAssertNil(pendingAfterSuccess)
    }

    func testNotificationTapForwardsOnlyStableDestinationToRouter() throws {
        let router = PushNotificationRouter()
        var received: NotificationDestination?
        router.setHandler { destination in
            received = destination
        }
        let appDelegate = LifeManagerAppDelegate(
            permissionService: PushPermissionStub(status: .denied, requestResult: false),
            registrar: RemoteNotificationRegistrarStub(),
            pushRouter: router,
            environment: .production
        )

        appDelegate.handleNotification(userInfo: [
            "aps": ["alert": ["title": "ignored"]],
            "type": "chat_message",
            "messageId": "message:v1:42",
            "cursor": "cursor:v1:42"
        ])

        XCTAssertEqual(received?.messageID, "message:v1:42")
        XCTAssertEqual(received?.cursor, "cursor:v1:42")
    }

    func testRouterRetainsPushUntilChatRegistersHandler() {
        let router = PushNotificationRouter()
        let destination = try! NotificationDestination(
            type: .chatMessage,
            messageID: "message:v1:pending",
            cursor: "cursor:v1:pending"
        )

        router.receive(destination)
        XCTAssertNil(router.currentHandlerDestination)

        var received: NotificationDestination?
        router.setHandler { value in
            received = value
        }

        XCTAssertEqual(received, destination)
    }
}

@MainActor
private final class PushPermissionStub: NotificationPermissionServicing {
    var status: NotificationAuthorizationStatus
    let requestResult: Bool
    private(set) var requestCount = 0

    init(status: NotificationAuthorizationStatus, requestResult: Bool) {
        self.status = status
        self.requestResult = requestResult
    }

    func authorizationStatus() async -> NotificationAuthorizationStatus { status }

    func requestAuthorization() async throws -> Bool {
        requestCount += 1
        status = requestResult ? .authorized : .denied
        return requestResult
    }
}

@MainActor
private final class RemoteNotificationRegistrarStub: RemoteNotificationRegistering {
    private(set) var registerCount = 0

    func registerForRemoteNotifications() {
        registerCount += 1
    }
}

@MainActor
private final class PushDeviceServiceStub: DeviceServicing {
    struct Registration: Equatable {
        let token: Data
        let environment: APNsEnvironment
        let locale: ProductLocale
        let timezone: String
    }

    private(set) var registration: Registration?
    private(set) var registrationCount = 0
    private(set) var registrations: [(token: Data, locale: ProductLocale, timezone: String, idempotencyKey: UUID)] = []
    private(set) var unregisterKeys: [UUID] = []
    private var failRegistration = false
    private var failUnregistration = false

    init(failRegistrationOnce: Bool = false, failUnregistrationOnce: Bool = false) {
        failRegistration = failRegistrationOnce
        failUnregistration = failUnregistrationOnce
    }

    func register(
        token: Data,
        environment: APNsEnvironment,
        locale: ProductLocale,
        timezone: String,
        idempotencyKey: UUID
    ) async throws {
        registrationCount += 1
        if failRegistration {
            failRegistration = false
            throw APIError.transport("offline")
        }
        registration = Registration(token: token, environment: environment, locale: locale, timezone: timezone)
        registrations.append((token, locale, timezone, idempotencyKey))
    }

    func unregister(idempotencyKey: UUID) async throws {
        unregisterKeys.append(idempotencyKey)
        if failUnregistration {
            failUnregistration = false
            throw APIError.transport("offline")
        }
    }
}
