import SwiftUI

enum RecommendationCategory: String {
    case food = "食"
    case movement = "動"
    case rest = "息"

    var localizedName: String {
        switch self {
        case .food: return NSLocalizedString("Food", comment: "")
        case .movement: return NSLocalizedString("Movement", comment: "")
        case .rest: return NSLocalizedString("Rest", comment: "")
        }
    }

    var sfSymbol: String {
        switch self {
        case .food: return "fork.knife"
        case .movement: return "figure.walk"
        case .rest: return "moon.fill"
        }
    }

    var color: Color {
        switch self {
        case .food: return Color(hex: "#A07840")
        case .movement: return Color(hex: "#5C8A4F")
        case .rest: return Color(hex: "#4472A8")
        }
    }
}

struct Recommendation {
    let category: RecommendationCategory
    let body: String
}
