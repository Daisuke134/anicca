import SwiftUI

enum FocusArea: String, Codable, CaseIterable, Identifiable {
    case confidence = "Confidence"
    case gratitude = "Gratitude"
    case calm = "Calm"
    case motivation = "Motivation"
    case selfLove = "Self-Love"

    var id: String { rawValue }

    var systemImage: String {
        switch self {
        case .confidence: return "star.fill"
        case .gratitude: return "heart.fill"
        case .calm: return "leaf.fill"
        case .motivation: return "flame.fill"
        case .selfLove: return "person.fill"
        }
    }

    var color: Color {
        switch self {
        case .confidence: return Color.yellow
        case .gratitude: return Color.pink
        case .calm: return Color.teal
        case .motivation: return Color.orange
        case .selfLove: return Color.purple
        }
    }

    var description: String {
        switch self {
        case .confidence: return "Believe in yourself"
        case .gratitude: return "Appreciate life"
        case .calm: return "Find inner peace"
        case .motivation: return "Stay driven"
        case .selfLove: return "Accept yourself"
        }
    }

    var prompt: String {
        switch self {
        case .confidence:
            return "Generate a positive affirmation about self-confidence and believing in one's abilities"
        case .gratitude:
            return "Generate a positive affirmation about gratitude and appreciation for life"
        case .calm:
            return "Generate a positive affirmation about inner peace and calmness"
        case .motivation:
            return "Generate a positive affirmation about motivation and drive to succeed"
        case .selfLove:
            return "Generate a positive affirmation about self-love and self-acceptance"
        }
    }
}
