import Foundation

struct StretchExercise: Codable, Identifiable {
    let id: String
    let name: String
    let category: PainArea
    let instructions: String
    let durationSeconds: Int
    let sfSymbol: String
    let isPremium: Bool
}
