import Foundation
import SwiftData

@Model
final class Affirmation {
    @Attribute(.unique) var id: UUID
    var content: String
    var focusAreaRaw: String
    var createdAt: Date
    var isFavorite: Bool

    var focusArea: FocusArea {
        get { FocusArea(rawValue: focusAreaRaw) ?? .calm }
        set { focusAreaRaw = newValue.rawValue }
    }

    init(content: String, focusArea: FocusArea) {
        self.id = UUID()
        self.content = content
        self.focusAreaRaw = focusArea.rawValue
        self.createdAt = Date()
        self.isFavorite = false
    }
}
