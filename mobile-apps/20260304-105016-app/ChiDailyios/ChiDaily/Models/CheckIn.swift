import Foundation
import SwiftData

@Model
final class CheckIn {
    var id: UUID
    var date: Date
    var energyLevel: Int
    var sleepQuality: Int
    var digestionComfort: Int
    var emotionalState: Int
    var physicalSensation: Int
    var constitutionType: String
    var foodRecommendation: String
    var movementRecommendation: String
    var restRecommendation: String
    var createdAt: Date

    init(
        id: UUID = UUID(),
        date: Date = Date(),
        energyLevel: Int,
        sleepQuality: Int,
        digestionComfort: Int,
        emotionalState: Int,
        physicalSensation: Int,
        constitutionType: String = "",
        foodRecommendation: String = "",
        movementRecommendation: String = "",
        restRecommendation: String = "",
        createdAt: Date = Date()
    ) {
        self.id = id
        self.date = date
        self.energyLevel = energyLevel
        self.sleepQuality = sleepQuality
        self.digestionComfort = digestionComfort
        self.emotionalState = emotionalState
        self.physicalSensation = physicalSensation
        self.constitutionType = constitutionType
        self.foodRecommendation = foodRecommendation
        self.movementRecommendation = movementRecommendation
        self.restRecommendation = restRecommendation
        self.createdAt = createdAt
    }
}
