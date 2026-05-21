import Foundation

enum BreathingType: String, CaseIterable, Identifiable {
    case box = "box"
    case fourSevenEight = "four_seven_eight"
    case physiologicalSigh = "physiological_sigh"

    var id: String { rawValue }

    var localizedName: String {
        switch self {
        case .box: return L10n.breathingBoxName
        case .fourSevenEight: return L10n.breathingFourSevenEightName
        case .physiologicalSigh: return L10n.breathingPhysiologicalSighName
        }
    }

    var description: String {
        switch self {
        case .box: return L10n.breathingBoxDescription
        case .fourSevenEight: return L10n.breathingFourSevenEightDescription
        case .physiologicalSigh: return L10n.breathingPhysiologicalSighDescription
        }
    }

    // Phase durations in seconds
    var phases: [BreathingPhase] {
        switch self {
        case .box:
            return [
                BreathingPhase(type: .inhale, duration: 4, label: L10n.breathingPhaseInhale),
                BreathingPhase(type: .hold, duration: 4, label: L10n.breathingPhaseHold),
                BreathingPhase(type: .exhale, duration: 4, label: L10n.breathingPhaseExhale),
                BreathingPhase(type: .hold, duration: 4, label: L10n.breathingPhaseHold)
            ]
        case .fourSevenEight:
            return [
                BreathingPhase(type: .inhale, duration: 4, label: L10n.breathingPhaseInhale),
                BreathingPhase(type: .hold, duration: 7, label: L10n.breathingPhaseHold),
                BreathingPhase(type: .exhale, duration: 8, label: L10n.breathingPhaseExhale)
            ]
        case .physiologicalSigh:
            return [
                BreathingPhase(type: .inhale, duration: 2, label: L10n.breathingPhaseInhale),
                BreathingPhase(type: .inhale, duration: 1, label: L10n.breathingPhaseInhale2),
                BreathingPhase(type: .exhale, duration: 8, label: L10n.breathingPhaseLongExhale)
            ]
        }
    }

    var totalCycleDuration: Double {
        phases.reduce(0) { $0 + $1.duration }
    }
}

enum BreathingPhaseType {
    case inhale
    case exhale
    case hold
}

struct BreathingPhase {
    let type: BreathingPhaseType
    let duration: Double
    let label: String
}

enum SessionDuration: Int, CaseIterable {
    case short = 60
    case medium = 180
    case long = 300

    var label: String {
        switch self {
        case .short: return "60s"
        case .medium: return "3m"
        case .long: return "5m"
        }
    }
}
