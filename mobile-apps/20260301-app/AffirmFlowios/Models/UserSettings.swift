import Foundation
import SwiftUI

@Observable
class UserSettings {
    @ObservationIgnored
    @AppStorage("selectedFocusAreas")
    var selectedFocusAreasData: Data = Data()

    @ObservationIgnored
    @AppStorage("onboardingComplete")
    var onboardingComplete: Bool = false

    @ObservationIgnored
    @AppStorage("dailyRefreshCount")
    var dailyRefreshCount: Int = 0

    @ObservationIgnored
    @AppStorage("lastRefreshDate")
    var lastRefreshDateInterval: Double = 0

    var selectedFocusAreas: [FocusArea] {
        get {
            guard let areas = try? JSONDecoder().decode([FocusArea].self, from: selectedFocusAreasData) else {
                return []
            }
            return areas
        }
        set {
            selectedFocusAreasData = (try? JSONEncoder().encode(newValue)) ?? Data()
        }
    }

    var lastRefreshDate: Date {
        get { Date(timeIntervalSince1970: lastRefreshDateInterval) }
        set { lastRefreshDateInterval = newValue.timeIntervalSince1970 }
    }

    static let freeLimit = 3

    var canRefresh: Bool {
        resetDailyCountIfNeeded()
        return dailyRefreshCount < Self.freeLimit
    }

    var refreshesRemaining: Int {
        resetDailyCountIfNeeded()
        return max(0, Self.freeLimit - dailyRefreshCount)
    }

    func incrementRefreshCount() {
        resetDailyCountIfNeeded()
        dailyRefreshCount += 1
        lastRefreshDate = Date()
    }

    private func resetDailyCountIfNeeded() {
        if !Calendar.current.isDateInToday(lastRefreshDate) {
            dailyRefreshCount = 0
        }
    }
}
