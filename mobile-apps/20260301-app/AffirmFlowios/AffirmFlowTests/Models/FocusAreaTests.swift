import Testing
import SwiftUI
@testable import AffirmFlow

struct FocusAreaTests {
    @Test
    func allCasesCount() {
        #expect(FocusArea.allCases.count == 5)
    }

    @Test(arguments: FocusArea.allCases)
    func hasSystemImage(area: FocusArea) {
        #expect(!area.systemImage.isEmpty)
    }

    @Test(arguments: FocusArea.allCases)
    func hasColor(area: FocusArea) {
        #expect(area.color != nil)
    }

    @Test(arguments: FocusArea.allCases)
    func hasDescription(area: FocusArea) {
        #expect(!area.description.isEmpty)
    }

    @Test(arguments: FocusArea.allCases)
    func hasPrompt(area: FocusArea) {
        #expect(!area.prompt.isEmpty)
        #expect(area.prompt.contains("affirmation"))
    }

    @Test
    func rawValueEncoding() {
        #expect(FocusArea.confidence.rawValue == "Confidence")
        #expect(FocusArea.selfLove.rawValue == "Self-Love")
        #expect(FocusArea.gratitude.rawValue == "Gratitude")
        #expect(FocusArea.calm.rawValue == "Calm")
        #expect(FocusArea.motivation.rawValue == "Motivation")
    }

    @Test
    func identifiableConformance() {
        #expect(FocusArea.confidence.id == "Confidence")
        #expect(FocusArea.calm.id == "Calm")
    }

    @Test
    func codableConformance() throws {
        let encoder = JSONEncoder()
        let decoder = JSONDecoder()

        let original = FocusArea.gratitude
        let data = try encoder.encode(original)
        let decoded = try decoder.decode(FocusArea.self, from: data)

        #expect(original == decoded)
    }

    @Test
    func systemImagesAreValid() {
        let expectedImages: [FocusArea: String] = [
            .confidence: "star.fill",
            .gratitude: "heart.fill",
            .calm: "leaf.fill",
            .motivation: "flame.fill",
            .selfLove: "person.fill"
        ]

        for (area, expectedImage) in expectedImages {
            #expect(area.systemImage == expectedImage)
        }
    }
}
