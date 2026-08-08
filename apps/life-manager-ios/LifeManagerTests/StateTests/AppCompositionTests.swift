import Foundation
import XCTest
@testable import LifeManager

@MainActor
final class AppCompositionTests: XCTestCase {
    func testOAuthOnboardingBootstrapsAuthoritativeProfileAfterExchangeAndPartialPatch() async throws {
        let transport = try OAuthBootstrapTransport(
            bootstrap: ContractFixtureLoader.data(named: "bootstrap.json"),
            profilePatch: ContractFixtureLoader.data(named: "profile-patch.json")
        )
        let callback = URL(string: "lifemanager://oauth/callback?state=state:v1:calendar-consent-8f3a&status=success&connected_account_id=ca_calendar_8f3a")!
        let composition = AppComposition(
            baseURL: URL(string: "https://life-manager.example/api/mobile/v1")!,
            callbackScheme: "lifemanager",
            transport: transport,
            sessionStore: CompositionSessionStore(),
            callbackAuthorizer: CompositionCallbackAuthorizer(callback: callback)
        )

        await composition.viewModel.connectCalendar()

        XCTAssertEqual(composition.viewModel.route, .profile)
        XCTAssertEqual(composition.viewModel.profile?.id, "user:v1:server-derived-8f3a")
        XCTAssertEqual(composition.viewModel.profile?.timezone, "America/Los_Angeles")
        XCTAssertEqual(composition.viewModel.profile?.offerStatus, .available)

        await composition.viewModel.submitProfile(ProfileDraft(name: "Alex Morgan", home: "100 Market Street"))

        XCTAssertEqual(composition.viewModel.route, .phone)
        XCTAssertEqual(composition.viewModel.profile?.id, "user:v1:server-derived-8f3a")
        XCTAssertEqual(composition.viewModel.profile?.timezone, "America/Los_Angeles")
        XCTAssertEqual(composition.viewModel.profile?.offerStatus, .available)
        let paths = await transport.paths()
        XCTAssertEqual(
            paths,
            [
                "/api/mobile/v1/session/calendar/start",
                "/api/mobile/v1/session/exchange",
                "/api/mobile/v1/bootstrap",
                "/api/mobile/v1/profile",
                "/api/mobile/v1/bootstrap"
            ]
        )
    }

    func testOAuthExchangePropagatesToSessionAPIAndRevokesBeforeWelcome() async throws {
        let store = CompositionSessionStore()
        let transport = OAuthLogoutTransport()
        let callback = URL(string: "lifemanager://oauth/callback?state=state:v1:calendar-consent-8f3a&status=success&connected_account_id=ca_calendar_8f3a")!
        let composition = AppComposition(
            baseURL: URL(string: "https://life-manager.example/api/mobile/v1")!,
            callbackScheme: "lifemanager",
            transport: transport,
            sessionStore: store,
            callbackAuthorizer: CompositionCallbackAuthorizer(callback: callback)
        )

        await composition.viewModel.connectCalendar()
        XCTAssertEqual(composition.viewModel.route, .profile)

        let signOutTask = Task { @MainActor in
            await composition.viewModel.settingsViewModel?.signOut()
        }
        await transport.waitForSessionRevokeRequest()

        XCTAssertNotEqual(composition.viewModel.route, .welcome)
        let requestsBeforeRelease = await transport.requestsSnapshot()
        let revokeRequest = try XCTUnwrap(
            requestsBeforeRelease.first { $0.httpMethod == "DELETE" && $0.url?.path == "/api/mobile/v1/session" }
        )
        XCTAssertEqual(revokeRequest.value(forHTTPHeaderField: "Authorization"), "Bearer oauth-access")
        let serverRevokeCount = await transport.serverRevokeCount()
        XCTAssertEqual(serverRevokeCount, 1)

        await transport.releaseSessionRevoke()
        await signOutTask.value

        XCTAssertEqual(composition.viewModel.route, .welcome)
        let storedSession = await store.currentSession()
        XCTAssertNil(storedSession)
    }
}

private struct CompositionCallbackAuthorizer: OAuthCallbackAuthorizing, Sendable {
    let callback: URL

    func authorize(url: URL, expectedState: String) async throws -> URL {
        callback
    }
}

private actor OAuthBootstrapTransport: HTTPTransport {
    private let session = Session(
        accessToken: "oauth-access",
        refreshToken: "oauth-refresh",
        tokenType: "Bearer",
        expiresAt: Date.iso8601("2026-08-10T08:20:00.000Z"),
        refreshExpiresAt: Date.iso8601("2026-09-09T08:05:00.000Z")
    )
    private let bootstrap: Data
    private let profilePatch: Data
    private var recordedPaths: [String] = []

    init(bootstrap: Data, profilePatch: Data) {
        self.bootstrap = bootstrap
        self.profilePatch = profilePatch
    }

    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let path = request.url?.path ?? ""
        recordedPaths.append(path)
        switch (request.httpMethod, path) {
        case ("POST", "/api/mobile/v1/session/calendar/start"):
            let body = Data(#"{"state":"state:v1:calendar-consent-8f3a","authorizationURL":"https://accounts.google.com/o/oauth2/v2/auth","expiresAt":"2026-08-10T08:05:00.000Z"}"#.utf8)
            return response(for: request, statusCode: 200, body: body)
        case ("POST", "/api/mobile/v1/session/exchange"):
            return response(for: request, statusCode: 200, body: try JSONEncoder.lifeManager.encode(session))
        case ("GET", "/api/mobile/v1/bootstrap"):
            return response(for: request, statusCode: 200, body: bootstrap)
        case ("PATCH", "/api/mobile/v1/profile"):
            return response(for: request, statusCode: 200, body: profilePatch)
        default:
            return response(for: request, statusCode: 404, body: Data())
        }
    }

    func paths() -> [String] { recordedPaths }

    private func response(for request: URLRequest, statusCode: Int, body: Data) -> (Data, HTTPURLResponse) {
        let response = HTTPURLResponse(
            url: request.url!,
            statusCode: statusCode,
            httpVersion: nil,
            headerFields: nil
        )!
        return (body, response)
    }
}

private actor CompositionSessionStore: SessionStoring {
    private var session: Session?

    func load() async throws -> Session? { session }
    func save(_ session: Session) async throws { self.session = session }
    func clear() async throws { session = nil }
    func currentSession() -> Session? { session }
}

private actor OAuthLogoutTransport: HTTPTransport {
    private let session = Session(
        accessToken: "oauth-access",
        refreshToken: "oauth-refresh",
        tokenType: "Bearer",
        expiresAt: Date.iso8601("2026-08-10T08:20:00.000Z"),
        refreshExpiresAt: Date.iso8601("2026-09-09T08:05:00.000Z")
    )
    private var requests: [URLRequest] = []
    private var revokeWaiters: [CheckedContinuation<Void, Never>] = []
    private var releaseWaiters: [CheckedContinuation<Void, Never>] = []
    private var revokeRequested = false
    private var revokeReleased = false
    private var revokeCount = 0

    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        requests.append(request)
        let path = request.url?.path ?? ""
        switch (request.httpMethod, path) {
        case ("POST", "/api/mobile/v1/session/calendar/start"):
            let body = Data(#"{"state":"state:v1:calendar-consent-8f3a","authorizationURL":"https://accounts.google.com/o/oauth2/v2/auth","expiresAt":"2026-08-10T08:05:00.000Z"}"#.utf8)
            return response(for: request, statusCode: 200, body: body)
        case ("POST", "/api/mobile/v1/session/exchange"):
            let body = try JSONEncoder.lifeManager.encode(session)
            return response(for: request, statusCode: 200, body: body)
        case ("GET", "/api/mobile/v1/bootstrap"):
            let body = try ContractFixtureLoader.data(named: "bootstrap.json")
            return response(for: request, statusCode: 200, body: body)
        case ("DELETE", "/api/mobile/v1/devices/apns"):
            return response(for: request, statusCode: 204, body: Data())
        case ("DELETE", "/api/mobile/v1/session"):
            revokeRequested = true
            revokeCount += 1
            let waiters = revokeWaiters
            revokeWaiters.removeAll()
            waiters.forEach { $0.resume() }
            if !revokeReleased {
                await withCheckedContinuation { continuation in
                    releaseWaiters.append(continuation)
                }
            }
            return response(for: request, statusCode: 204, body: Data())
        default:
            return response(for: request, statusCode: 404, body: Data())
        }
    }

    func waitForSessionRevokeRequest() async {
        if revokeRequested { return }
        await withCheckedContinuation { continuation in
            revokeWaiters.append(continuation)
        }
    }

    func releaseSessionRevoke() {
        revokeReleased = true
        let waiters = releaseWaiters
        releaseWaiters.removeAll()
        waiters.forEach { $0.resume() }
    }

    func requestsSnapshot() -> [URLRequest] { requests }
    func serverRevokeCount() -> Int { revokeCount }

    private func response(for request: URLRequest, statusCode: Int, body: Data) -> (Data, HTTPURLResponse) {
        let response = HTTPURLResponse(
            url: request.url!,
            statusCode: statusCode,
            httpVersion: nil,
            headerFields: nil
        )!
        return (body, response)
    }
}
