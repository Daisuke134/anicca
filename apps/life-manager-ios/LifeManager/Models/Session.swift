import Foundation

struct Session: Codable, Equatable, Sendable {
    let accessToken: String
    let refreshToken: String
    let tokenType: String
    let expiresAt: Date
    let refreshExpiresAt: Date

    var isExpired: Bool {
        expiresAt <= Date()
    }
}

struct SessionStart: Codable, Equatable, Sendable {
    let state: String
    let authorizationURL: URL
    let expiresAt: Date
}
