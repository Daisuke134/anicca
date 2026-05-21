import Foundation
import SwiftData
import SwiftUI

@Observable
@MainActor
class AppViewModel {
    var language: AppLanguage {
        didSet { UserDefaults.standard.set(language.rawValue, forKey: "app_language") }
    }
    var hasCompletedOnboarding: Bool {
        didSet { UserDefaults.standard.set(hasCompletedOnboarding, forKey: "has_onboarded") }
    }
    var isPro: Bool = false

    var currentAffirmation: Affirmation = AffirmationData.random()

    init() {
        self.language = .english
        self.hasCompletedOnboarding = UserDefaults.standard.bool(forKey: "has_onboarded")
    }

    func refreshAffirmation() {
        currentAffirmation = AffirmationData.random()
    }

    func calculateStreak(entries: [GratitudeEntry]) -> Int {
        let calendar = Calendar.current
        let sortedDates = Set(entries.map { calendar.startOfDay(for: $0.date) }).sorted(by: >)

        guard !sortedDates.isEmpty else { return 0 }

        let today = calendar.startOfDay(for: Date())
        let yesterday = calendar.date(byAdding: .day, value: -1, to: today)!

        guard sortedDates[0] == today || sortedDates[0] == yesterday else { return 0 }

        var streak = 1
        for i in 1..<sortedDates.count {
            let expected = calendar.date(byAdding: .day, value: -i, to: sortedDates[0])!
            if sortedDates[i] == expected {
                streak += 1
            } else {
                break
            }
        }
        return streak
    }

    func hasTodayEntry(entries: [GratitudeEntry]) -> Bool {
        let today = Calendar.current.startOfDay(for: Date())
        return entries.contains { Calendar.current.startOfDay(for: $0.date) == today }
    }

    func entryCount(entries: [GratitudeEntry]) -> Int {
        entries.count
    }
}
