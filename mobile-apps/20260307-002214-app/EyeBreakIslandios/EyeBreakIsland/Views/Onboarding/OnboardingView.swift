import SwiftUI

struct OnboardingView: View {
    @StateObject private var viewModel: OnboardingViewModel
    @EnvironmentObject var subscriptionService: SubscriptionService

    init(notificationService: NotificationServiceProtocol = NotificationService()) {
        _viewModel = StateObject(wrappedValue: OnboardingViewModel(notificationService: notificationService))
    }

    var body: some View {
        VStack {
            TabView(selection: $viewModel.currentPage) {
                ForEach(Array(viewModel.pages.enumerated()), id: \.offset) { index, page in
                    VStack {
                        OnboardingPageView(page: page, pageIndex: index)

                        if index == 2 {
                            notificationButton
                        } else {
                            nextButton
                        }

                        pageIndicator
                            .padding(.bottom, AppSpacing.xl)
                    }
                    .tag(index)
                }

                paywallPage
                    .tag(3)
            }
            .tabViewStyle(.page(indexDisplayMode: .never))
            .animation(AppAnimations.pageTransition, value: viewModel.currentPage)
        }
        .accessibilityIdentifier(AccessibilityID.onboardingContainer)
    }

    // MARK: - Subviews

    private var nextButton: some View {
        PrimaryButton(title: "Next") {
            viewModel.nextPage()
        }
        .padding(.horizontal, AppSpacing.lg)
        .accessibilityIdentifier(AccessibilityID.onboardingNextButton)
    }

    private var notificationButton: some View {
        PrimaryButton(title: "Allow Notifications") {
            Task { await viewModel.requestNotificationPermission() }
        }
        .padding(.horizontal, AppSpacing.lg)
        .accessibilityIdentifier(AccessibilityID.onboardingAllowNotifications)
    }

    private var pageIndicator: some View {
        HStack(spacing: AppSpacing.xs) {
            ForEach(0..<viewModel.totalPages, id: \.self) { index in
                Circle()
                    .fill(index == viewModel.currentPage ? AppColors.brandPrimary : AppColors.textTertiary)
                    .frame(width: 8, height: 8)
            }
        }
        .padding(.top, AppSpacing.md)
    }

    private var paywallPage: some View {
        PaywallView(
            subscriptionService: subscriptionService,
            onDismiss: {
                viewModel.completeOnboarding()
            },
            onPurchaseCompleted: {
                viewModel.completeOnboarding()
            }
        )
    }
}
