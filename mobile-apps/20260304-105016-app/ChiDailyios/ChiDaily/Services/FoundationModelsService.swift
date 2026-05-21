import Foundation

actor FoundationModelsService {
    func analyze(
        energy: Int, sleep: Int, digestion: Int, emotion: Int, physical: Int
    ) async throws -> (ConstitutionType, [Recommendation]) {
        return ruleBasedAnalysis(energy: energy, sleep: sleep, digestion: digestion, emotion: emotion, physical: physical)
    }

    private func ruleBasedAnalysis(
        energy: Int, sleep: Int, digestion: Int, emotion: Int, physical: Int
    ) -> (ConstitutionType, [Recommendation]) {
        let scores = computeScores(energy: energy, sleep: sleep, digestion: digestion, emotion: emotion, physical: physical)
        let constitution = scores.max(by: { $0.value < $1.value })?.key ?? .earth
        let recommendations = buildRecommendations(for: constitution)
        return (constitution, recommendations)
    }

    private func computeScores(energy: Int, sleep: Int, digestion: Int, emotion: Int, physical: Int) -> [ConstitutionType: Int] {
        var scores: [ConstitutionType: Int] = [.wood: 0, .fire: 0, .earth: 0, .metal: 0, .water: 0]
        scores[.wood]! += (6 - emotion) + (6 - physical)
        scores[.fire]! += (6 - sleep) + emotion
        scores[.earth]! += (6 - energy) + (6 - digestion)
        scores[.metal]! += (6 - energy) + (6 - physical)
        scores[.water]! += (6 - energy) * 2 + (6 - sleep)
        return scores
    }

    private func buildRecommendations(for constitution: ConstitutionType) -> [Recommendation] {
        switch constitution {
        case .wood:
            return [
                Recommendation(category: .food, body: NSLocalizedString("Sour foods and green leafy vegetables support liver health.", comment: "")),
                Recommendation(category: .movement, body: NSLocalizedString("Gentle stretching and yoga release muscle tension.", comment: "")),
                Recommendation(category: .rest, body: NSLocalizedString("Sleep before 11pm to nourish the liver's regeneration cycle.", comment: ""))
            ]
        case .fire:
            return [
                Recommendation(category: .food, body: NSLocalizedString("Bitter greens and red berries calm heart fire.", comment: "")),
                Recommendation(category: .movement, body: NSLocalizedString("Light walking or gentle cardio balances heart energy.", comment: "")),
                Recommendation(category: .rest, body: NSLocalizedString("Practice 5-minute mindful breathing before bed.", comment: ""))
            ]
        case .earth:
            return [
                Recommendation(category: .food, body: NSLocalizedString("Warm, cooked root vegetables and miso soup support digestion.", comment: "")),
                Recommendation(category: .movement, body: NSLocalizedString("A 20-minute walk after meals strengthens spleen qi.", comment: "")),
                Recommendation(category: .rest, body: NSLocalizedString("Avoid worry by journaling thoughts before sleep.", comment: ""))
            ]
        case .metal:
            return [
                Recommendation(category: .food, body: NSLocalizedString("White foods like daikon, pear, and almonds nourish lung yin.", comment: "")),
                Recommendation(category: .movement, body: NSLocalizedString("Deep breathing exercises and qigong support lung function.", comment: "")),
                Recommendation(category: .rest, body: NSLocalizedString("Allow time for grief—it's healthy to process emotions.", comment: ""))
            ]
        case .water:
            return [
                Recommendation(category: .food, body: NSLocalizedString("Dark foods like black sesame, kidney beans, and seaweed fortify kidney jing.", comment: "")),
                Recommendation(category: .movement, body: NSLocalizedString("Slow, restorative practices like yin yoga preserve vital energy.", comment: "")),
                Recommendation(category: .rest, body: NSLocalizedString("Prioritize 8+ hours of sleep to replenish kidney essence.", comment: ""))
            ]
        }
    }
}

enum FoundationModelsError: Error {
    case parseFailure
}
