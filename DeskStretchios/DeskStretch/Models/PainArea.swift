import Foundation

enum PainArea: String, Codable, CaseIterable, Identifiable {
    case neck
    case back
    case shoulders
    case wrists

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .neck: return String(localized: "Neck")
        case .back: return String(localized: "Lower Back")
        case .shoulders: return String(localized: "Shoulders")
        case .wrists: return String(localized: "Wrists")
        }
    }

    var sfSymbol: String {
        switch self {
        case .neck: return "person.crop.circle"
        case .back: return "figure.seated.side"
        case .shoulders: return "figure.arms.open"
        case .wrists: return "hand.raised"
        }
    }
}
