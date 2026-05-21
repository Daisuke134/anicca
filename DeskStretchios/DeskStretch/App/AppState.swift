import Foundation
import Observation

@Observable
class AppState {
    var selectedPainAreas: Set<PainArea> = []
    var breakSchedule: BreakSchedule = .default
    var userProgress: UserProgress = .empty
    var isPremium: Bool = false
    var hasCompletedOnboarding: Bool = false
    var currentSession: StretchSession? = nil

    private let defaults = UserDefaults.standard

    func loadPersistedState() {
        hasCompletedOnboarding = defaults.bool(forKey: "hasCompletedOnboarding")

        if let data = defaults.data(forKey: "selectedPainAreas"),
           let areas = try? JSONDecoder().decode(Set<PainArea>.self, from: data) {
            selectedPainAreas = areas
        }

        if let data = defaults.data(forKey: "breakSchedule"),
           let schedule = try? JSONDecoder().decode(BreakSchedule.self, from: data) {
            breakSchedule = schedule
        }

        if let data = defaults.data(forKey: "userProgress"),
           let progress = try? JSONDecoder().decode(UserProgress.self, from: data) {
            userProgress = progress
        }
    }

    func persistOnboardingComplete() {
        hasCompletedOnboarding = true
        defaults.set(true, forKey: "hasCompletedOnboarding")
        persistPainAreas()
        persistBreakSchedule()
    }

    func persistPainAreas() {
        if let data = try? JSONEncoder().encode(selectedPainAreas) {
            defaults.set(data, forKey: "selectedPainAreas")
        }
    }

    func persistBreakSchedule() {
        if let data = try? JSONEncoder().encode(breakSchedule) {
            defaults.set(data, forKey: "breakSchedule")
        }
    }

    func persistProgress() {
        if let data = try? JSONEncoder().encode(userProgress) {
            defaults.set(data, forKey: "userProgress")
        }
    }
}
