import Foundation

enum TemperatureUnit: String, Codable {
    case celsius, fahrenheit
}

enum ExperienceLevel: String, Codable {
    case beginner, intermediate, advanced
}

struct UserPreferences {
    private enum Keys {
        static let temperatureUnit = "temperature_unit"
        static let notificationsEnabled = "notifications_enabled"
        static let reminderTime = "reminder_time"
        static let hasCompletedOnboarding = "has_completed_onboarding"
        static let experienceLevel = "experience_level"
        static let currentStreak = "current_streak"
        static let longestStreak = "longest_streak"
        static let lastPlungeDate = "last_plunge_date"
        static let streakFreezeUsedThisWeek = "streak_freeze_used_this_week"
        static let appLaunchCount = "app_launch_count"
    }

    private let defaults: UserDefaults

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    var temperatureUnit: TemperatureUnit {
        get {
            guard let raw = defaults.string(forKey: Keys.temperatureUnit),
                  let unit = TemperatureUnit(rawValue: raw) else { return .celsius }
            return unit
        }
        nonmutating set { defaults.set(newValue.rawValue, forKey: Keys.temperatureUnit) }
    }

    var notificationsEnabled: Bool {
        get { defaults.bool(forKey: Keys.notificationsEnabled) }
        nonmutating set { defaults.set(newValue, forKey: Keys.notificationsEnabled) }
    }

    var reminderTime: Date? {
        get {
            let interval = defaults.double(forKey: Keys.reminderTime)
            return interval > 0 ? Date(timeIntervalSince1970: interval) : nil
        }
        nonmutating set { defaults.set(newValue?.timeIntervalSince1970 ?? 0, forKey: Keys.reminderTime) }
    }

    var hasCompletedOnboarding: Bool {
        get { defaults.bool(forKey: Keys.hasCompletedOnboarding) }
        nonmutating set { defaults.set(newValue, forKey: Keys.hasCompletedOnboarding) }
    }

    var experienceLevel: ExperienceLevel {
        get {
            guard let raw = defaults.string(forKey: Keys.experienceLevel),
                  let level = ExperienceLevel(rawValue: raw) else { return .beginner }
            return level
        }
        nonmutating set { defaults.set(newValue.rawValue, forKey: Keys.experienceLevel) }
    }

    var currentStreak: Int {
        get { defaults.integer(forKey: Keys.currentStreak) }
        nonmutating set { defaults.set(newValue, forKey: Keys.currentStreak) }
    }

    var longestStreak: Int {
        get { defaults.integer(forKey: Keys.longestStreak) }
        nonmutating set { defaults.set(newValue, forKey: Keys.longestStreak) }
    }

    var lastPlungeDate: Date? {
        get {
            let interval = defaults.double(forKey: Keys.lastPlungeDate)
            return interval > 0 ? Date(timeIntervalSince1970: interval) : nil
        }
        nonmutating set { defaults.set(newValue?.timeIntervalSince1970 ?? 0, forKey: Keys.lastPlungeDate) }
    }

    var streakFreezeUsedThisWeek: Bool {
        get { defaults.bool(forKey: Keys.streakFreezeUsedThisWeek) }
        nonmutating set { defaults.set(newValue, forKey: Keys.streakFreezeUsedThisWeek) }
    }

    var appLaunchCount: Int {
        get { defaults.integer(forKey: Keys.appLaunchCount) }
        nonmutating set { defaults.set(newValue, forKey: Keys.appLaunchCount) }
    }
}
