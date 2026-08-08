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

    func register(
        token: Data,
        environment: APNsEnvironment,
        locale: ProductLocale,
        timezone: String,
        idempotencyKey: UUID
    ) async throws {
        registrationCount += 1
        registration = Registration(token: token, environment: environment, locale: locale, timezone: timezone)
    }

    func unregister(idempotencyKey: UUID) async throws {}
}
