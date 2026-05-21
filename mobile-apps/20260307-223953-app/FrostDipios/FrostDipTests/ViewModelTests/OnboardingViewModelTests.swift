import XCTest
@testable import FrostDip

final class OnboardingViewModelTests: XCTestCase {
    private var sut: OnboardingViewModel!
    private var defaults: UserDefaults!

    override func setUp() {
        super.setUp()
        defaults = UserDefaults(suiteName: "OnboardingViewModelTests")!
        defaults.removePersistentDomain(forName: "OnboardingViewModelTests")
        sut = OnboardingViewModel(defaults: defaults)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: "OnboardingViewModelTests")
        sut = nil
        defaults = nil
        super.tearDown()
    }

    // MARK: - Initial State

    func testInitialStepIsWelcome() {
        XCTAssertEqual(sut.currentStep, .welcome)
    }

    func testInitialExperienceLevelIsNil() {
        XCTAssertNil(sut.selectedExperienceLevel)
    }

    // MARK: - Step Navigation

    func testAdvanceFromWelcomeToExperience() {
        sut.advance()
        XCTAssertEqual(sut.currentStep, .experience)
    }

    func testAdvanceFromExperienceToNotification() {
        sut.currentStep = .experience
        sut.selectedExperienceLevel = .beginner
        sut.advance()
        XCTAssertEqual(sut.currentStep, .notification)
    }

    func testAdvanceFromNotificationToPaywall() {
        sut.currentStep = .notification
        sut.advance()
        XCTAssertEqual(sut.currentStep, .paywall)
    }

    func testCannotAdvanceFromExperienceWithoutSelection() {
        sut.currentStep = .experience
        sut.selectedExperienceLevel = nil
        sut.advance()
        XCTAssertEqual(sut.currentStep, .experience, "Should stay on experience without selection")
    }

    // MARK: - Experience Level Persistence

    func testSelectExperienceLevelSavesToDefaults() {
        sut.selectExperienceLevel(.advanced)
        let prefs = UserPreferences(defaults: defaults)
        XCTAssertEqual(prefs.experienceLevel, .advanced)
    }

    func testSelectExperienceLevelUpdatesProperty() {
        sut.selectExperienceLevel(.intermediate)
        XCTAssertEqual(sut.selectedExperienceLevel, .intermediate)
    }

    // MARK: - Complete Onboarding

    func testCompleteOnboardingSetsFlag() {
        sut.completeOnboarding()
        let prefs = UserPreferences(defaults: defaults)
        XCTAssertTrue(prefs.hasCompletedOnboarding)
    }

    // MARK: - Step Enum

    func testStepOrderIsCorrect() {
        let steps: [OnboardingStep] = [.welcome, .experience, .notification, .paywall]
        for i in 0..<steps.count - 1 {
            XCTAssertTrue(steps[i].rawValue < steps[i + 1].rawValue)
        }
    }
}
