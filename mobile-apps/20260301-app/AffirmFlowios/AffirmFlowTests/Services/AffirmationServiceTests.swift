import Testing
@testable import AffirmFlow

struct AffirmationServiceTests {
    @Test
    func serviceInitializes() {
        let service = AffirmationService()
        #expect(service != nil)
    }

    @Test(arguments: FocusArea.allCases)
    func promptContainsAffirmation(area: FocusArea) {
        let prompt = area.prompt
        #expect(prompt.lowercased().contains("affirmation"))
    }

    @Test
    func generateAffirmationReturnsContent() async throws {
        let service = AffirmationService()
        let result = try await service.generateAffirmation(for: .calm)

        #expect(!result.isEmpty)
    }

    @Test(arguments: FocusArea.allCases)
    func generateAffirmationForAllAreas(area: FocusArea) async throws {
        let service = AffirmationService()
        let result = try await service.generateAffirmation(for: area)

        #expect(!result.isEmpty)
        #expect(result.count > 10) // Affirmations should be meaningful length
    }

    @Test
    func errorDescriptions() {
        let modelError = AffirmationService.AffirmationError.modelUnavailable
        let genError = AffirmationService.AffirmationError.generationFailed

        #expect(modelError.errorDescription?.isEmpty == false)
        #expect(genError.errorDescription?.isEmpty == false)
    }

    @Test
    func multipleGenerationsReturnContent() async throws {
        let service = AffirmationService()

        for _ in 1...3 {
            let result = try await service.generateAffirmation(for: .confidence)
            #expect(!result.isEmpty)
        }
    }
}
