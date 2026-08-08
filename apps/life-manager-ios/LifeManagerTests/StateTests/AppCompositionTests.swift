import Foundation
import XCTest
@testable import LifeManager

@MainActor
final class AppCompositionTests: XCTestCase {
    func testOAuthExchangePropagatesToSessionAPIAndRevokesBeforeWelcome() async throws {
        let store = CompositionSessionStore()
        let transport = OAuthLogoutTransport()
        let callback = URL(string: "lifemanager://oauth/callback?code=one-use-code&state=state:v1:calendar-consent-8f3a")!
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
