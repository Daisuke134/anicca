import Foundation
import XCTest
@testable import LifeManager

final class APIClientTests: XCTestCase {
    func testCursorQueryRemainsAQueryInTheRealURL() async throws {
        let store = InMemorySessionStore(session: TestSessionFactory.make())
        let transport = ScriptedTransport(statuses: [200], payload: Data(#"{"value":"ok"}"#.utf8))
        let client = APIClient(
            baseURL: URL(string: "https://life-manager.example/api/mobile/v1")!,
            transport: transport,
            sessionStore: store,
            refresh: { _ in XCTFail("refresh should not run"); throw APIError.refreshRejected }
        )

        let endpoint = APIEndpoint.get(path: "/chat?cursor=cursor:v1/a?next")
        _ = try await client.send(endpoint, as: ValueResponse.self)

        let requests = await transport.requestsSnapshot()
        let request = try XCTUnwrap(requests.first)
        XCTAssertEqual(request.url?.path, "/api/mobile/v1/chat")
        XCTAssertEqual(request.url?.query, "cursor=cursor:v1/a?next")
        XCTAssertEqual(
            URLComponents(url: try XCTUnwrap(request.url), resolvingAgainstBaseURL: false)?
                .queryItems?.first(where: { $0.name == "cursor" })?.value,
            "cursor:v1/a?next"
        )
    }

    func testRequestAddsBearerAndMutationIdempotencyHeaders() async throws {
        let store = InMemorySessionStore(session: TestSessionFactory.make(accessToken: "access-token"))
        let transport = ScriptedTransport(statuses: [200], payload: Data(#"{"value":"ok"}"#.utf8))
        let client = APIClient(
            baseURL: URL(string: "https://life-manager.example")!,
            transport: transport,
            sessionStore: store,
            refresh: { _ in XCTFail("refresh should not run"); throw APIError.refreshRejected }
        )
        let key = UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!

        let response: ValueResponse = try await client.send(
            .mutation(path: "/profile", method: .patch, body: Data(#"{"name":"A"}"#.utf8)),
            as: ValueResponse.self,
            idempotencyKey: key
        )

        XCTAssertEqual(response, ValueResponse(value: "ok"))
        let requests = await transport.requestsSnapshot()
        XCTAssertEqual(requests.count, 1)
        XCTAssertEqual(requests[0].value(forHTTPHeaderField: "Authorization"), "Bearer access-token")
        XCTAssertEqual(requests[0].value(forHTTPHeaderField: "Idempotency-Key"), key.uuidString)
        XCTAssertEqual(requests[0].httpMethod, "PATCH")
        XCTAssertEqual(requests[0].url?.path, "/profile")
    }

    func testConcurrentUnauthorizedRequestsPerformOneRefreshAndReplayTheirOriginalKeys() async throws {
        let oldSession = TestSessionFactory.make(accessToken: "old-access")
        let rotatedSession = TestSessionFactory.make(accessToken: "rotated-access")
        let store = InMemorySessionStore(session: oldSession)
        let gate = AsyncGate()
        let transport = ScriptedTransport(
            statuses: [401, 401, 200, 200],
            payload: Data(#"{"value":"ok"}"#.utf8),
            gate: gate,
            gatedResponseCount: 2
        )
        let refreshProbe = RefreshProbe(rotatedSession: rotatedSession)
        let client = APIClient(
            baseURL: URL(string: "https://life-manager.example")!,
            transport: transport,
            sessionStore: store,
            refresh: { session in try await refreshProbe.refresh(session) }
        )
        let firstKey = UUID(uuidString: "11111111-2222-3333-4444-555555555555")!
        let secondKey = UUID(uuidString: "66666666-7777-8888-9999-AAAAAAAAAAAA")!
        let endpoint = APIEndpoint.mutation(path: "/analysis", method: .post, body: Data(#"{"request":1}"#.utf8))

        async let first: ValueResponse = client.send(endpoint, as: ValueResponse.self, idempotencyKey: firstKey)
        async let second: ValueResponse = client.send(endpoint, as: ValueResponse.self, idempotencyKey: secondKey)
        await transport.waitForRequestCount(2)
        await gate.open()
        _ = try await (first, second)

        let refreshCount = await refreshProbe.count()
        XCTAssertEqual(refreshCount, 1)
        let savedSession = await store.currentSession()
        XCTAssertEqual(savedSession, rotatedSession)
        let requests = await transport.requestsSnapshot()
        XCTAssertEqual(requests.count, 4)
        for key in [firstKey.uuidString, secondKey.uuidString] {
            let matching = requests.filter { $0.value(forHTTPHeaderField: "Idempotency-Key") == key }
            XCTAssertEqual(matching.count, 2)
            XCTAssertEqual(Set(matching.compactMap { $0.value(forHTTPHeaderField: "Authorization") }), ["Bearer old-access", "Bearer rotated-access"])
        }
    }

    func testRefreshFamilyRejectionClearsSessionAndSurfacesStructuredError() async throws {
        let store = InMemorySessionStore(session: TestSessionFactory.make())
        let transport = ScriptedTransport(statuses: [401], payload: Data())
        let client = APIClient(
            baseURL: URL(string: "https://life-manager.example")!,
            transport: transport,
            sessionStore: store,
            refresh: { _ in throw RefreshFamilyRejected() }
        )

        do {
            let _: ValueResponse = try await client.send(.get(path: "/bootstrap"), as: ValueResponse.self)
            XCTFail("expected refresh rejection")
        } catch let error as APIError {
            XCTAssertEqual(error, .refreshRejected)
        }

        let currentSession = await store.currentSession()
        let clearCount = await store.clearCount()
        XCTAssertNil(currentSession)
        XCTAssertEqual(clearCount, 1)
    }
}

private struct ValueResponse: Codable, Equatable, Sendable {
    let value: String
}

private enum TestSessionFactory {
    static func make(accessToken: String = "access-token") -> Session {
        Session(
            accessToken: accessToken,
            refreshToken: "refresh-token",
            tokenType: "Bearer",
            expiresAt: Date.iso8601("2026-08-10T08:20:00.000Z"),
            refreshExpiresAt: Date.iso8601("2026-09-09T08:05:00.000Z")
        )
    }
}

private actor InMemorySessionStore: SessionStoring {
    private var session: Session?
    private var clears = 0

    init(session: Session?) {
        self.session = session
    }

    func load() async throws -> Session? { session }
    func save(_ session: Session) async throws { self.session = session }
    func clear() async throws { session = nil; clears += 1 }
    func currentSession() -> Session? { session }
    func clearCount() -> Int { clears }
}

private actor RefreshProbe {
    private let rotatedSession: Session
    private var calls = 0

    init(rotatedSession: Session) {
        self.rotatedSession = rotatedSession
    }

    func refresh(_ session: Session) async throws -> Session {
        calls += 1
        return rotatedSession
    }

    func count() -> Int { calls }
}

private struct RefreshFamilyRejected: Error, Sendable {}

private actor AsyncGate {
    private var isOpen = false
    private var waiters: [CheckedContinuation<Void, Never>] = []

    func wait() async {
        if isOpen { return }
        await withCheckedContinuation { continuation in
            waiters.append(continuation)
        }
    }

    func open() {
        isOpen = true
        let pending = waiters
        waiters.removeAll()
        pending.forEach { $0.resume() }
    }
}

private actor ScriptedTransport: HTTPTransport {
    private let statuses: [Int]
    private let payload: Data
    private let gate: AsyncGate?
    private let gatedResponseCount: Int
    private var responseIndex = 0
    private var requests: [URLRequest] = []
    private var countWaiters: [(Int, CheckedContinuation<Void, Never>)] = []

    init(statuses: [Int], payload: Data, gate: AsyncGate? = nil, gatedResponseCount: Int = 0) {
        self.statuses = statuses
        self.payload = payload
        self.gate = gate
        self.gatedResponseCount = gatedResponseCount
    }

    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let index = responseIndex
        responseIndex += 1
        requests.append(request)
        let ready = countWaiters.filter { requests.count >= $0.0 }
        countWaiters.removeAll { requests.count >= $0.0 }
        ready.forEach { $0.1.resume() }
        if index < gatedResponseCount {
            await gate?.wait()
        }
        let status = statuses[min(index, statuses.count - 1)]
        return (payload, HTTPURLResponse(
            url: request.url!,
            statusCode: status,
            httpVersion: nil,
            headerFields: nil
        )!)
    }

    func waitForRequestCount(_ count: Int) async {
        if requests.count >= count { return }
        await withCheckedContinuation { continuation in
            countWaiters.append((count, continuation))
        }
    }

    func requestsSnapshot() -> [URLRequest] { requests }
}
