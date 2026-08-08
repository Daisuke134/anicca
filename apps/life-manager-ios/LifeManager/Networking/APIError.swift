import Foundation

enum APIError: Error, Equatable, Sendable {
    case invalidURL
    case invalidResponse
    case noSession
    case unauthorized
    case refreshRejected
    case server(statusCode: Int)
    case decodingFailed
    case transport(String)
    case invalidAPNsToken
    case missingIdempotencyKey
}
