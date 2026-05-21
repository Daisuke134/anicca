import Testing
@testable import ChiDaily

struct FoundationModelsServiceTests {

    let service = FoundationModelsService()

    @Test func analyzeReturnsConstitutionAndRecommendations() async throws {
        let (constitution, recommendations) = try await service.analyze(
            energy: 3, sleep: 3, digestion: 3, emotion: 3, physical: 3
        )
        _ = constitution
        #expect(!recommendations.isEmpty)
    }

    @Test func lowEnergyLowSleepReturnsResult() async throws {
        let (constitution, recommendations) = try await service.analyze(
            energy: 1, sleep: 1, digestion: 3, emotion: 3, physical: 3
        )
        _ = constitution
        #expect(!recommendations.isEmpty)
    }

    @Test func allHighValuesReturnsResult() async throws {
        let (_, recommendations) = try await service.analyze(
            energy: 5, sleep: 5, digestion: 5, emotion: 5, physical: 5
        )
        #expect(!recommendations.isEmpty)
    }

    @Test func recommendationsHaveAllCategories() async throws {
        let (_, recommendations) = try await service.analyze(
            energy: 3, sleep: 3, digestion: 3, emotion: 3, physical: 3
        )
        let categories = Set(recommendations.map { $0.category })
        #expect(categories.contains(.food))
        #expect(categories.contains(.movement))
        #expect(categories.contains(.rest))
    }
}
