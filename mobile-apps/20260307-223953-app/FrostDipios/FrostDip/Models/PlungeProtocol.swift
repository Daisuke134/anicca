import Foundation
import SwiftData

@Model
final class PlungeProtocol {
    var id: UUID
    var name: String
    var prepTime: TimeInterval
    var coldTime: TimeInterval
    var hotTime: TimeInterval
    var rounds: Int
    var restTime: TimeInterval
    var isDefault: Bool
    var createdAt: Date

    init(name: String, prepTime: TimeInterval, coldTime: TimeInterval, hotTime: TimeInterval = 0, rounds: Int = 1, restTime: TimeInterval = 0) {
        self.id = UUID()
        self.name = name
        self.prepTime = prepTime
        self.coldTime = coldTime
        self.hotTime = hotTime
        self.rounds = rounds
        self.restTime = restTime
        self.isDefault = false
        self.createdAt = Date()
    }

    static func defaultProtocols() -> [PlungeProtocol] {
        let beginner = PlungeProtocol(name: "Beginner", prepTime: 60, coldTime: 60)
        beginner.isDefault = true

        let intermediate = PlungeProtocol(name: "Intermediate", prepTime: 60, coldTime: 180)
        intermediate.isDefault = true

        let advanced = PlungeProtocol(name: "Advanced", prepTime: 30, coldTime: 300)
        advanced.isDefault = true

        let contrast = PlungeProtocol(name: "Contrast Therapy", prepTime: 60, coldTime: 120, hotTime: 180, rounds: 3, restTime: 30)
        contrast.isDefault = true

        return [beginner, intermediate, advanced, contrast]
    }
}
