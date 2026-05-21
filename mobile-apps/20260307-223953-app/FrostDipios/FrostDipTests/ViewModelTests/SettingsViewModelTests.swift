import XCTest
@testable import FrostDip

final class SettingsViewModelTests: XCTestCase {
    private var sut: SettingsViewModel!
    private var defaults: UserDefaults!

    override func setUp() {
        super.setUp()
        defaults = UserDefaults(suiteName: "SettingsViewModelTests")!
        defaults.removePersistentDomain(forName: "SettingsViewModelTests")
        sut = SettingsViewModel(defaults: defaults)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: "SettingsViewModelTests")
        sut = nil
        defaults = nil
        super.tearDown()
    }

    // MARK: - Temperature Unit

    func testDefaultTemperatureUnitIsCelsius() {
        XCTAssertEqual(sut.temperatureUnit, .celsius)
    }

    func testToggleTemperatureUnit() {
        sut.setTemperatureUnit(.fahrenheit)
        XCTAssertEqual(sut.temperatureUnit, .fahrenheit)
    }

    func testTemperatureUnitPersistsToDefaults() {
        sut.setTemperatureUnit(.fahrenheit)
        let prefs = UserPreferences(defaults: defaults)
        XCTAssertEqual(prefs.temperatureUnit, .fahrenheit)
    }

    // MARK: - Notifications

    func testDefaultNotificationsDisabled() {
        XCTAssertFalse(sut.notificationsEnabled)
    }

    func testToggleNotificationsUpdatesPrefs() {
        sut.notificationsEnabled = true
        let prefs = UserPreferences(defaults: defaults)
        XCTAssertTrue(prefs.notificationsEnabled)
    }

    // MARK: - Show Paywall

    func testShowPaywallDefaultsFalse() {
        XCTAssertFalse(sut.showPaywall)
    }

    func testTapUpgradeShowsPaywall() {
        sut.tapUpgrade()
        XCTAssertTrue(sut.showPaywall)
    }

    // MARK: - App Version

    func testAppVersionIsNotEmpty() {
        XCTAssertFalse(sut.appVersion.isEmpty)
    }
}
