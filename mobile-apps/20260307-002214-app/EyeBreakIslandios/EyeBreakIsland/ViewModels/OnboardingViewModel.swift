import SwiftUI

struct OnboardingPageData {
    let iconName: String
    let titleKey: String
    let subtitleKey: String
}

@MainActor
final class OnboardingViewModel: ObservableObject {
    @Published var currentPage: Int = 0

    let totalPages: Int = 4
    let notificationService: NotificationServiceProtocol

    let pages: [OnboardingPageData] = [
        OnboardingPageData(
            iconName: "eye",
            titleKey: "onboarding.welcome.title",
            subtitleKey: "onboarding.welcome.subtitle"
        ),
        OnboardingPageData(
            iconName: "timer",
            titleKey: "onboarding.feature.title",
            subtitleKey: "onboarding.feature.subtitle"
        ),
        OnboardingPageData(
            iconName: "bell.fill",
            titleKey: "onboarding.notification.title",
            subtitleKey: "onboarding.notification.subtitle"
        )
    ]

    var canGoNext: Bool {
        currentPage < totalPages - 1
    }

    init(notificationService: NotificationServiceProtocol = NotificationService()) {
        self.notificationService = notificationService
    }

    func nextPage() {
        guard canGoNext else { return }
        currentPage += 1
    }

    func requestNotificationPermission() async {
        _ = await notificationService.requestPermission()
        if currentPage < totalPages - 1 {
            currentPage += 1
        }
    }

    func completeOnboarding() {
        UserDefaults.standard.set(true, forKey: Constants.hasCompletedOnboardingKey)
    }

    static var isOnboardingCompleted: Bool {
        UserDefaults.standard.bool(forKey: Constants.hasCompletedOnboardingKey)
    }
}
