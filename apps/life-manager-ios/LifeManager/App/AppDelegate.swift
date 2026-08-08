import Foundation
import UIKit
import UserNotifications

enum NotificationAuthorizationStatus: Equatable, Sendable {
    case notDetermined
    case denied
    case authorized
    case provisional
    case ephemeral

    var permitsRemoteRegistration: Bool {
        switch self {
        case .authorized, .provisional, .ephemeral:
            return true
        case .notDetermined, .denied:
            return false
        }
    }
}

@MainActor
protocol NotificationPermissionServicing: AnyObject {
    func authorizationStatus() async -> NotificationAuthorizationStatus
    func requestAuthorization() async throws -> Bool
}

@MainActor
private final class SystemNotificationPermissionService: NotificationPermissionServicing {
    private let center: UNUserNotificationCenter

    init(center: UNUserNotificationCenter = .current()) {
        self.center = center
    }

    func authorizationStatus() async -> NotificationAuthorizationStatus {
        let settings = await center.notificationSettings()
        switch settings.authorizationStatus {
        case .notDetermined:
            return .notDetermined
        case .denied:
            return .denied
        case .authorized:
            return .authorized
        case .provisional:
            return .provisional
        case .ephemeral:
            return .ephemeral
        @unknown default:
            return .denied
        }
    }

    func requestAuthorization() async throws -> Bool {
        try await center.requestAuthorization(options: [.alert, .badge, .sound])
    }
}

@MainActor
protocol RemoteNotificationRegistering: AnyObject {
    func registerForRemoteNotifications()
}

@MainActor
private final class SystemRemoteNotificationRegistrar: RemoteNotificationRegistering {
    func registerForRemoteNotifications() {
        UIApplication.shared.registerForRemoteNotifications()
    }
}

@MainActor
final class PushNotificationRouter {
    static let shared = PushNotificationRouter()

    private var pendingDestination: NotificationDestination?
    private var handler: (@MainActor (NotificationDestination) -> Void)?
    private(set) var currentHandlerDestination: NotificationDestination?

    func setHandler(_ handler: @escaping @MainActor (NotificationDestination) -> Void) {
        self.handler = handler
        guard let pendingDestination else { return }
        self.pendingDestination = nil
        currentHandlerDestination = pendingDestination
        handler(pendingDestination)
    }

    func clearHandler() {
        handler = nil
    }

    func receive(_ destination: NotificationDestination) {
        guard let handler else {
            pendingDestination = destination
            return
        }
        currentHandlerDestination = destination
        handler(destination)
    }
}

@MainActor
final class LifeManagerAppDelegate: NSObject, UIApplicationDelegate, @preconcurrency UNUserNotificationCenterDelegate {
    private let permissionService: NotificationPermissionServicing
    private let registrar: RemoteNotificationRegistering
    private let pushRouter: PushNotificationRouter
    private let environment: APNsEnvironment
    private let notificationCenter: UNUserNotificationCenter?
    private let retryStore: OperationRetryStoring

    private var registrationWasRequested = false
    private var deviceService: DeviceServicing?
    private var deviceLocale: ProductLocale = .en
    private var deviceTimezone = TimeZone.current.identifier
    private var hasConfiguredDeviceState = false
    private var pendingDeviceToken: Data?
    private var lastRegisteredDeviceToken: Data?
    private var registrationInFlight = false
    private var registrationRetryRequested = false

    private(set) var lastDeviceRegistrationError: AppErrorState?

    init(
        permissionService: NotificationPermissionServicing,
        registrar: RemoteNotificationRegistering,
        pushRouter: PushNotificationRouter,
        environment: APNsEnvironment,
        notificationCenter: UNUserNotificationCenter? = nil,
        retryStore: OperationRetryStoring = UserDefaultsOperationRetryStore()
    ) {
        self.permissionService = permissionService
        self.registrar = registrar
        self.pushRouter = pushRouter
        self.environment = environment
        self.notificationCenter = notificationCenter
        self.retryStore = retryStore
        super.init()
    }

    override convenience init() {
        let center = UNUserNotificationCenter.current()
        self.init(
            permissionService: SystemNotificationPermissionService(center: center),
            registrar: SystemRemoteNotificationRegistrar(),
            pushRouter: .shared,
            environment: .current,
            notificationCenter: center
        )
    }

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        notificationCenter?.delegate = self
        return true
    }

    func requestAuthorizationAndRegisterIfNeeded() async throws -> Bool {
        switch await permissionService.authorizationStatus() {
        case .authorized, .provisional, .ephemeral:
            requestRemoteRegistration()
            return true
        case .denied:
            return false
        case .notDetermined:
            guard try await permissionService.requestAuthorization() else { return false }
            requestRemoteRegistration()
            return true
        }
    }

    func configure(
        deviceService: DeviceServicing,
        locale: ProductLocale,
        timezone: String
    ) {
        self.deviceService = deviceService
        deviceLocale = locale
        deviceTimezone = timezone
        hasConfiguredDeviceState = true
        guard registrationWasRequested, pendingDeviceToken != nil else { return }
        Task { await registerPendingDeviceTokenIfReady() }
    }

    func updateDeviceLocale(_ locale: ProductLocale, timezone: String) async {
        let changed = deviceLocale != locale || deviceTimezone != timezone
        deviceLocale = locale
        deviceTimezone = timezone
        guard changed else { return }
        if pendingDeviceToken == nil {
            pendingDeviceToken = lastRegisteredDeviceToken
        }
        lastRegisteredDeviceToken = nil
        await registerPendingDeviceTokenIfReady()
    }

    func unregisterDevice() async throws {
        guard let deviceService else { return }
        let operationKey = await retryStore.operationKey(for: .deviceUnregistration)
        do {
            try await deviceService.unregister(idempotencyKey: operationKey)
            await retryStore.clear(.deviceUnregistration)
            pendingDeviceToken = nil
            lastRegisteredDeviceToken = nil
            lastDeviceRegistrationError = nil
        } catch {
            await retryStore.clearIfDefinitive(.deviceUnregistration, after: error)
            lastDeviceRegistrationError = AppErrorState(error: error)
            throw error
        }
    }

    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        Task { await registerDeviceToken(deviceToken) }
    }

    func registerDeviceToken(_ deviceToken: Data) async {
        pendingDeviceToken = deviceToken
        await registerPendingDeviceTokenIfReady()
    }

    func retryDeviceRegistration() async {
        await registerPendingDeviceTokenIfReady()
    }

    func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        lastDeviceRegistrationError = AppErrorState(error: error)
    }

    func handleNotification(userInfo: [AnyHashable: Any]) {
        guard let destination = NotificationDestination(userInfo: userInfo) else { return }
        pushRouter.receive(destination)
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        handleNotification(userInfo: notification.request.content.userInfo)
        completionHandler([.banner, .sound])
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse,
        withCompletionHandler completionHandler: @escaping () -> Void
    ) {
        handleNotification(userInfo: response.notification.request.content.userInfo)
        completionHandler()
    }

    private func requestRemoteRegistration() {
        guard !registrationWasRequested else { return }
        registrationWasRequested = true
        registrar.registerForRemoteNotifications()
    }

    private func registerPendingDeviceTokenIfReady() async {
        if registrationInFlight {
            registrationRetryRequested = true
            return
        }
        registrationInFlight = true
        defer {
            registrationInFlight = false
            if registrationRetryRequested {
                registrationRetryRequested = false
                Task { @MainActor [weak self] in
                    await self?.registerPendingDeviceTokenIfReady()
                }
            }
        }
        await restorePendingDeviceRegistrationIfNeeded()
        guard
            registrationWasRequested,
            let pendingDeviceToken,
            pendingDeviceToken.count == 32,
            pendingDeviceToken != lastRegisteredDeviceToken,
            let deviceService
        else {
            return
        }

        let proposedRequest = DeviceRegistrationRequest(
            token: pendingDeviceToken.map { String(format: "%02x", $0) }.joined(),
            environment: environment,
            locale: deviceLocale,
            timezone: deviceTimezone
        )
        let pending = await retryStore.pending(for: .deviceRegistration)
        let request: DeviceRegistrationRequest
        if
            let pending,
            let input = pending.input,
            let persistedRequest = try? JSONDecoder.lifeManager.decode(DeviceRegistrationRequest.self, from: input),
            persistedRequest.token == proposedRequest.token
        {
            request = persistedRequest
        } else {
            request = proposedRequest
        }
        let operationKey: UUID
        if
            let pending,
            let input = pending.input,
            let persistedRequest = try? JSONDecoder.lifeManager.decode(DeviceRegistrationRequest.self, from: input),
            persistedRequest.token == proposedRequest.token
        {
            operationKey = pending.idempotencyKey
        } else {
            let body = try? JSONEncoder.lifeManager.encode(request)
            operationKey = await retryStore.operationKey(for: .deviceRegistration, input: body)
        }

        do {
            let token = try Self.data(fromHex: request.token)
            try await deviceService.register(
                token: token,
                environment: request.environment,
                locale: request.locale,
                timezone: request.timezone,
                idempotencyKey: operationKey
            )
            await retryStore.clear(.deviceRegistration)
            let desiredStateChanged = deviceLocale != request.locale || deviceTimezone != request.timezone
            if desiredStateChanged {
                lastRegisteredDeviceToken = nil
                self.pendingDeviceToken = token
                registrationRetryRequested = true
            } else {
                lastRegisteredDeviceToken = token
                self.pendingDeviceToken = nil
            }
            lastDeviceRegistrationError = nil
        } catch {
            await retryStore.clearIfDefinitive(.deviceRegistration, after: error)
            lastDeviceRegistrationError = AppErrorState(error: error)
        }
    }

    private func restorePendingDeviceRegistrationIfNeeded() async {
        guard pendingDeviceToken == nil else { return }
        guard
            let pending = await retryStore.pending(for: .deviceRegistration),
            let input = pending.input,
            let request = try? JSONDecoder.lifeManager.decode(DeviceRegistrationRequest.self, from: input),
            let token = try? Self.data(fromHex: request.token)
        else {
            return
        }
        pendingDeviceToken = token
        if !hasConfiguredDeviceState {
            deviceLocale = request.locale
            deviceTimezone = request.timezone
        }
    }

    private static func data(fromHex value: String) throws -> Data {
        let bytes = Array(value.utf8)
        guard bytes.count.isMultiple(of: 2) else { throw APIError.invalidAPNsToken }
        var result: [UInt8] = []
        result.reserveCapacity(bytes.count / 2)
        for index in stride(from: 0, to: bytes.count, by: 2) {
            guard let byte = UInt8(String(bytes: bytes[index..<(index + 2)], encoding: .utf8) ?? "", radix: 16) else {
                throw APIError.invalidAPNsToken
            }
            result.append(byte)
        }
        guard result.count == 32 else { throw APIError.invalidAPNsToken }
        return Data(result)
    }
}

extension APNsEnvironment {
    static var current: Self {
        #if DEBUG
        return .sandbox
        #else
        return .production
        #endif
    }
}
