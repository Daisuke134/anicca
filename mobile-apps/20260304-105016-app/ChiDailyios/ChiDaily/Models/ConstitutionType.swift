import SwiftUI

enum ConstitutionType: String, CaseIterable, Codable {
    case wood = "Wood"
    case fire = "Fire"
    case earth = "Earth"
    case metal = "Metal"
    case water = "Water"

    var japaneseName: String {
        switch self {
        case .wood: return "木のタイプ"
        case .fire: return "火のタイプ"
        case .earth: return "土のタイプ"
        case .metal: return "金のタイプ"
        case .water: return "水のタイプ"
        }
    }

    var icon: String {
        switch self {
        case .wood: return "leaf.fill"
        case .fire: return "flame.fill"
        case .earth: return "mountain.2.fill"
        case .metal: return "circle.hexagongrid.fill"
        case .water: return "drop.fill"
        }
    }

    var color: Color {
        switch self {
        case .wood: return Color(hex: "#5C8A4F")
        case .fire: return Color(hex: "#C85A3C")
        case .earth: return Color(hex: "#A07840")
        case .metal: return Color(hex: "#888888")
        case .water: return Color(hex: "#4472A8")
        }
    }

    static func from(string: String) -> ConstitutionType {
        ConstitutionType(rawValue: string) ?? .earth
    }
}
