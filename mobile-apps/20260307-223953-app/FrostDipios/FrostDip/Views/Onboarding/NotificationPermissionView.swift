import SwiftUI

struct NotificationPermissionView: View {
    var onComplete: () -> Void

    @State private var isRequesting = false
    private let notificationService = NotificationService()

    var body: some View {
        VStack(spacing: Theme.Spacing.lg) {
            Spacer()

            Image(systemName: "bell.badge")
                .font(.system(size: 64))
                .foregroundStyle(Theme.Colors.accent)

            Text("Stay consistent with daily reminders")
                .font(Theme.Typography.title2)
                .multilineTextAlignment(.center)
                .foregroundStyle(Theme.Colors.label)
                .padding(.horizontal, Theme.Spacing.lg)

            VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
                benefitRow(icon: "clock.badge.checkmark", text: "Daily plunge reminders at your preferred time")
                benefitRow(icon: "flame", text: "Streak warnings before you lose your progress")
                benefitRow(icon: "chart.line.uptrend.xyaxis", text: "Weekly progress summaries")
            }
            .padding(.horizontal, Theme.Spacing.xl)

            Spacer()

            VStack(spacing: Theme.Spacing.sm) {
                Button(action: requestPermission) {
                    if isRequesting {
                        ProgressView()
                            .tint(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, Theme.Spacing.md)
                    } else {
                        Text("Enable Notifications")
                            .font(Theme.Typography.headline)
                            .foregroundStyle(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, Theme.Spacing.md)
                    }
                }
                .background(Theme.Colors.primary)
                .clipShape(RoundedRectangle(cornerRadius: Theme.CornerRadius.medium))
                .disabled(isRequesting)
                .accessibilityIdentifier(AccessibilityID.onboardingEnableNotifications)

                Button(action: onComplete) {
                    Text("Not Now")
                        .font(Theme.Typography.subheadline)
                        .foregroundStyle(Theme.Colors.secondaryLabel)
                }
                .accessibilityIdentifier(AccessibilityID.onboardingSkipNotifications)
            }
            .padding(.horizontal, Theme.Spacing.lg)
            .padding(.bottom, Theme.Spacing.xl)
        }
    }

    private func benefitRow(icon: String, text: String) -> some View {
        HStack(spacing: Theme.Spacing.sm) {
            Image(systemName: icon)
                .foregroundStyle(Theme.Colors.accent)
                .frame(width: 24)
            Text(text)
                .font(Theme.Typography.body)
                .foregroundStyle(Theme.Colors.label)
        }
    }

    private func requestPermission() {
        isRequesting = true
        Task {
            _ = try? await notificationService.requestPermission()
            await MainActor.run {
                isRequesting = false
                onComplete()
            }
        }
    }
}
