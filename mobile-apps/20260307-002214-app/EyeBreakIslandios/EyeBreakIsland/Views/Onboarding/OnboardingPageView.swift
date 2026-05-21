import SwiftUI

struct OnboardingPageView: View {
    let page: OnboardingPageData
    let pageIndex: Int

    var body: some View {
        VStack(spacing: AppSpacing.lg) {
            Spacer()

            Image(systemName: page.iconName)
                .font(.system(size: 80))
                .foregroundStyle(AppColors.brandPrimary)

            Text(LocalizedStringKey(page.titleKey))
                .font(AppTypography.headline1)
                .multilineTextAlignment(.center)

            Text(LocalizedStringKey(page.subtitleKey))
                .font(AppTypography.body)
                .foregroundStyle(AppColors.textSecondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, AppSpacing.xl)

            Spacer()
        }
        .accessibilityIdentifier(accessibilityID(for: pageIndex))
    }

    private func accessibilityID(for index: Int) -> String {
        switch index {
        case 0: return AccessibilityID.onboardingPage1
        case 1: return AccessibilityID.onboardingPage2
        case 2: return AccessibilityID.onboardingPage3
        default: return ""
        }
    }
}
