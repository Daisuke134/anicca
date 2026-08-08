import Foundation

protocol APIRequesting: Sendable {
    func send<Response: Decodable & Sendable>(
        _ endpoint: APIEndpoint,
        as responseType: Response.Type,
        idempotencyKey: UUID?
    ) async throws -> Response
    func sendVoid(_ endpoint: APIEndpoint, idempotencyKey: UUID?) async throws
}

actor APIClient: APIRequesting, SessionPropagating {
    typealias Refresh = @Sendable (Session) async throws -> Session

    private let baseURL: URL
    private let transport: HTTPTransport
    private let sessionStore: SessionStoring
    private let refresh: Refresh
    private var session: Session?
    private var didLoadSession = false
    private var sessionLoadTask: Task<Session?, Error>?
    private var refreshTask: Task<Session, Error>?
    private var lastRefresh: (failedAccessToken: String, session: Session)?

    init(
        baseURL: URL,
        transport: HTTPTransport = URLSessionTransport(),
        sessionStore: SessionStoring,
        refresh: @escaping Refresh
    ) {
        self.baseURL = baseURL
        self.transport = transport
        self.sessionStore = sessionStore
        self.refresh = refresh
    }

    func setSession(_ session: Session?) {
        sessionLoadTask?.cancel()
        sessionLoadTask = nil
        self.session = session
        didLoadSession = true
        lastRefresh = nil
    }

    func send<Response: Decodable & Sendable>(
        _ endpoint: APIEndpoint,
        as responseType: Response.Type,
        idempotencyKey: UUID? = nil
    ) async throws -> Response {
        let data = try await request(endpoint, idempotencyKey: idempotencyKey, retryAfterRefresh: true)
        do {
            return try JSONDecoder.lifeManager.decode(responseType, from: data)
        } catch {
            throw APIError.decodingFailed
        }
    }

    func sendVoid(_ endpoint: APIEndpoint, idempotencyKey: UUID? = nil) async throws {
        _ = try await request(endpoint, idempotencyKey: idempotencyKey, retryAfterRefresh: true)
    }

    private func request(
        _ endpoint: APIEndpoint,
        idempotencyKey: UUID?,
        retryAfterRefresh: Bool,
        sessionOverride: Session? = nil
    ) async throws -> Data {
        let session: Session?
        if let sessionOverride {
            session = sessionOverride
        } else {
            session = try await currentSession(required: endpoint.requiresAuthentication)
        }
        let resolvedIdempotencyKey: UUID?
        if endpoint.requiresIdempotencyKey {
            guard let idempotencyKey else {
                throw APIError.missingIdempotencyKey
            }
            resolvedIdempotencyKey = idempotencyKey
        } else {
            resolvedIdempotencyKey = idempotencyKey
        }
        let urlRequest = try makeRequest(
            endpoint,
            session: session,
            idempotencyKey: resolvedIdempotencyKey
        )
        let data: Data
        let response: HTTPURLResponse
        do {
            (data, response) = try await transport.data(for: urlRequest)
        } catch let error as APIError {
            throw error
        } catch {
            throw APIError.transport(String(describing: error))
        }

        guard response.statusCode != 401 else {
            guard retryAfterRefresh, endpoint.requiresAuthentication else {
                throw APIError.unauthorized
            }
            let rotatedSession = try await refreshOnce(afterFailedAccessToken: session?.accessToken)
            return try await request(
                endpoint,
                idempotencyKey: resolvedIdempotencyKey,
                retryAfterRefresh: false,
                sessionOverride: rotatedSession
            )
        }
        guard (200..<300).contains(response.statusCode) else {
            throw APIError.server(statusCode: response.statusCode)
        }
        return data
    }

    private func makeRequest(
        _ endpoint: APIEndpoint,
        session: Session?,
        idempotencyKey: UUID?
    ) throws -> URLRequest {
        guard
            var baseComponents = URLComponents(url: baseURL, resolvingAgainstBaseURL: false),
            let endpointComponents = URLComponents(string: endpoint.path)
        else {
            throw APIError.invalidURL
        }

        let basePath = baseComponents.path == "/" ? "" : baseComponents.path
        let endpointPath = endpointComponents.path.hasPrefix("/")
            ? endpointComponents.path
            : "/\(endpointComponents.path)"
        baseComponents.path = basePath + endpointPath
        baseComponents.queryItems = endpointComponents.queryItems
        guard let url = baseComponents.url else {
            throw APIError.invalidURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = endpoint.method.rawValue
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body = endpoint.body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        if let session {
            request.setValue(
                "\(session.tokenType) \(session.accessToken)",
                forHTTPHeaderField: "Authorization"
            )
        }
        if endpoint.requiresIdempotencyKey {
            guard let idempotencyKey else {
                throw APIError.missingIdempotencyKey
            }
            request.setValue(
                idempotencyKey.uuidString,
                forHTTPHeaderField: "Idempotency-Key"
            )
        }
        return request
    }

    private func currentSession(required: Bool) async throws -> Session? {
        if didLoadSession {
            guard !required || session != nil else { throw APIError.noSession }
            return session
        }
        if let sessionLoadTask {
            let loaded = try await sessionLoadTask.value
            guard !required || loaded != nil else { throw APIError.noSession }
            return loaded
        }

        let store = sessionStore
        let task = Task { try await store.load() }
        sessionLoadTask = task
        do {
            let loaded = try await task.value
            session = loaded
            didLoadSession = true
            sessionLoadTask = nil
            guard !required || loaded != nil else { throw APIError.noSession }
            return loaded
        } catch {
            sessionLoadTask = nil
            throw error
        }
    }

    private func refreshOnce(afterFailedAccessToken: String?) async throws -> Session {
        if let refreshTask {
            return try await refreshTask.value
        }
        if
            let afterFailedAccessToken,
            let lastRefresh,
            lastRefresh.failedAccessToken == afterFailedAccessToken
        {
            return lastRefresh.session
        }
        guard let currentSession = try await currentSession(required: true) else {
            throw APIError.noSession
        }

        let refresh = self.refresh
        let store = sessionStore
        let task = Task { () throws -> Session in
            do {
                let rotated = try await refresh(currentSession)
                try await store.save(rotated)
                return rotated
            } catch {
                try? await store.clear()
                throw APIError.refreshRejected
            }
        }
        refreshTask = task
        do {
            let rotated = try await task.value
            session = rotated
            didLoadSession = true
            if let afterFailedAccessToken {
                lastRefresh = (afterFailedAccessToken, rotated)
            }
            refreshTask = nil
            return rotated
        } catch {
            session = nil
            didLoadSession = true
            lastRefresh = nil
            refreshTask = nil
            throw error
        }
    }
}
