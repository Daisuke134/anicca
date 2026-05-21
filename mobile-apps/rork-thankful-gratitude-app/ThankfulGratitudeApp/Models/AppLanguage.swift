import Foundation

nonisolated enum AppLanguage: String, Codable, Sendable, CaseIterable {
    case english = "en"
    case japanese = "ja"

    var displayName: String {
        switch self {
        case .english: return "English"
        case .japanese: return "日本語"
        }
    }
}
