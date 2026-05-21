import Foundation

@Observable
final class SettingsViewModel {
    var temperatureUnit: TemperatureUnit
    var notificationsEnabled: Bool {
        didSet { preferences.notificationsEnabled = notificationsEnabled }
    }
    var showPaywall = false

    private let preferences: UserPreferences

    var appVersion: String {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0.0"
    }

    init(defaults: UserDefaults = .standard) {
        self.preferences = UserPreferences(defaults: defaults)
        self.temperatureUnit = preferences.temperatureUnit
        self.notificationsEnabled = preferences.notificationsEnabled
    }

    func setTemperatureUnit(_ unit: TemperatureUnit) {
        temperatureUnit = unit
        preferences.temperatureUnit = unit
    }

    func tapUpgrade() {
        showPaywall = true
    }
}
