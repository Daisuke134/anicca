import Foundation

@Observable
class AffirmationService {
    enum AffirmationError: LocalizedError {
        case modelUnavailable
        case generationFailed

        var errorDescription: String? {
            switch self {
            case .modelUnavailable:
                return "AI model is not available on this device"
            case .generationFailed:
                return "Unable to generate affirmation"
            }
        }
    }

    // Pre-defined affirmations for each focus area (fallback when AI is unavailable)
    private let affirmations: [FocusArea: [String]] = [
        .confidence: [
            "I believe in my abilities and trust my journey",
            "I am capable of achieving my goals",
            "I embrace challenges as opportunities to grow",
            "I have the power to create positive change",
            "I am confident in who I am becoming"
        ],
        .gratitude: [
            "I am grateful for the abundance in my life",
            "I appreciate every moment and experience",
            "I find joy in the little things today",
            "I am thankful for my unique journey",
            "I celebrate the blessings around me"
        ],
        .calm: [
            "I am at peace with who I am",
            "I release tension and embrace serenity",
            "I breathe deeply and feel centered",
            "I let go of what I cannot control",
            "I create calm in every moment"
        ],
        .motivation: [
            "I am driven by my purpose and passion",
            "I take action towards my dreams today",
            "I am unstoppable in pursuing my goals",
            "I turn obstacles into stepping stones",
            "I am motivated by my vision of success"
        ],
        .selfLove: [
            "I accept myself completely as I am",
            "I am worthy of love and happiness",
            "I treat myself with kindness and respect",
            "I honor my needs and boundaries",
            "I am enough exactly as I am"
        ]
    ]

    func generateAffirmation(for focusArea: FocusArea) async throws -> String {
        // For now, return a random pre-defined affirmation
        // FoundationModels requires iOS 26+ which will be supported in a future update
        guard let affirmationsForArea = affirmations[focusArea],
              let randomAffirmation = affirmationsForArea.randomElement() else {
            throw AffirmationError.generationFailed
        }

        // Simulate async behavior
        try await Task.sleep(nanoseconds: 500_000_000)

        return randomAffirmation
    }
}
