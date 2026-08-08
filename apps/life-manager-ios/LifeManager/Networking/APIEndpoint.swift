import Foundation

enum HTTPMethod: String, Sendable {
    case get = "GET"
    case post = "POST"
    case patch = "PATCH"
    case put = "PUT"
    case delete = "DELETE"
}

struct APIEndpoint: Equatable, Sendable {
    let path: String
    let method: HTTPMethod
    let body: Data?
    let requiresAuthentication: Bool
    let requiresIdempotencyKey: Bool

    static func get(path: String, requiresAuthentication: Bool = true) -> Self {
        Self(
            path: path,
            method: .get,
            body: nil,
            requiresAuthentication: requiresAuthentication,
            requiresIdempotencyKey: false
        )
    }

    static func mutation(path: String, method: HTTPMethod, body: Data? = nil) -> Self {
        Self(
            path: path,
            method: method,
            body: body,
            requiresAuthentication: true,
            requiresIdempotencyKey: true
        )
    }

    static func unauthenticatedMutation(path: String, method: HTTPMethod, body: Data? = nil) -> Self {
        Self(
            path: path,
            method: method,
            body: body,
            requiresAuthentication: false,
            requiresIdempotencyKey: true
        )
    }
}
