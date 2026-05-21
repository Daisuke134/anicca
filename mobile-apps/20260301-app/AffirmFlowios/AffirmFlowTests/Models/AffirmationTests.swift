import Testing
import Foundation
@testable import AffirmFlow

struct AffirmationTests {
    @Test
    func initializesWithCorrectValues() {
        let affirmation = Affirmation(content: "Test content", focusArea: .calm)

        #expect(affirmation.content == "Test content")
        #expect(affirmation.focusArea == .calm)
        #expect(affirmation.isFavorite == false)
        #expect(affirmation.id != nil)
    }

    @Test
    func createdAtIsNow() {
        let before = Date()
        let affirmation = Affirmation(content: "Test", focusArea: .calm)
        let after = Date()

        #expect(affirmation.createdAt >= before)
        #expect(affirmation.createdAt <= after)
    }

    @Test
    func favoriteToggle() {
        let affirmation = Affirmation(content: "Test", focusArea: .calm)
        #expect(affirmation.isFavorite == false)

        affirmation.isFavorite = true
        #expect(affirmation.isFavorite == true)

        affirmation.isFavorite = false
        #expect(affirmation.isFavorite == false)
    }

    @Test
    func focusAreaAccessor() {
        let affirmation = Affirmation(content: "Test", focusArea: .gratitude)
        #expect(affirmation.focusArea == .gratitude)

        affirmation.focusArea = .motivation
        #expect(affirmation.focusArea == .motivation)
    }

    @Test
    func focusAreaRawStorage() {
        let affirmation = Affirmation(content: "Test", focusArea: .confidence)
        #expect(affirmation.focusAreaRaw == "Confidence")

        affirmation.focusAreaRaw = "Calm"
        #expect(affirmation.focusArea == .calm)
    }

    @Test
    func uniqueIdentifiers() {
        let a1 = Affirmation(content: "Test 1", focusArea: .calm)
        let a2 = Affirmation(content: "Test 2", focusArea: .calm)

        #expect(a1.id != a2.id)
    }

    @Test(arguments: FocusArea.allCases)
    func initializesWithAllFocusAreas(area: FocusArea) {
        let affirmation = Affirmation(content: "Test for \(area.rawValue)", focusArea: area)
        #expect(affirmation.focusArea == area)
        #expect(affirmation.focusAreaRaw == area.rawValue)
    }
}
