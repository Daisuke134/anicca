import Foundation

enum OnboardingStep: Int, Comparable {
    case welcome = 0
    case experience = 1
    case notification = 2
    case paywall = 3

    static func < (lhs: OnboardingStep, rhs: OnboardingStep) -> Bool {
        lhs.rawValue < rhs.rawValue
    }
}

@Observable
final class OnboardingViewModel {
    var currentStep: OnboardingStep = .welcome
    var selectedExperienceLevel: ExperienceLevel?

    private let preferences: UserPreferences

    init(defaults: UserDefaults = .standard) {
        self.preferences = UserPreferences(defaults: defaults)
    }

    func advance() {
        switch currentStep {
        case .welcome:
            currentStep = .experience
        case .experience:
            guard selectedExperienceLevel != nil else { return }
            currentStep = .notification
        case .notification:
            currentStep = .paywall
        case .paywall:
            break
        }
    }

    func selectExperienceLevel(_ level: ExperienceLevel) {
        selectedExperienceLevel = level
        preferences.experienceLevel = level
    }

    func completeOnboarding() {
        preferences.hasCompletedOnboarding = true
    }
}
