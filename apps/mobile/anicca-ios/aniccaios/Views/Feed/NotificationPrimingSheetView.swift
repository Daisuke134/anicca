import SwiftUI
import UIKit

/// Second-chance notification priming, presented as a sheet from the feed
/// after a value moment (anicca-ops Issue #48). Same priming content as the
/// onboarding step — the actual notification, with the user's own goal
/// quote and the real delivery times — shown again to users who skipped
/// the onboarding ask and are still `.notDetermined`.
/// All strings reuse the onboarding localization keys.
struct NotificationPrimingSheetView: View {
    let finish: () -> Void

    @ObservedObject private var appState = AppState.shared
    @State private var isRequesting = false
    @State private var hasTrackedPriming = false

    /// Same goal → quote mapping as the onboarding priming preview and
    /// `FirstAffirmationStepView`.
    private var previewQuote: Quote {
        let quoteIDs = ["self_love": "q013", "calm": "q021", "confidence": "q041", "letting_go": "q071"]
        let id = quoteIDs[appState.userProfile.goals.first ?? "self_love"] ?? "q013"
        return QuoteProvider.shared.byId(id, preferredLanguage: appState.effectiveLanguage)
            ?? QuoteProvider.shared.all(preferredLanguage: appState.effectiveLanguage)[0]
    }

    var body: some View {
        VStack(spacing: 24) {
            Text(String(localized: "onboarding_notifications_title"))
                .font(.system(size: 32, weight: .bold))
                .foregroundStyle(AppTheme.Colors.label)
                .padding(.top, 40)

            Text(String(localized: "onboarding_notifications_description"))
                .font(.system(size: 16))
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)

            // Lock-screen preview of the actual notification.
            VStack(alignment: .leading, spacing: 10) {
                HStack(spacing: 10) {
                    Image("AniccaLogo")
                        .resizable()
                        .scaledToFill()
                        .frame(width: 30, height: 30)
                        .clipShape(RoundedRectangle(cornerRadius: 7))

                    Text("Anicca")
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundStyle(AppTheme.Colors.label)

                    Spacer()

                    Text(String(localized: "onboarding_notifications_preview_now"))
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                }

                Text(previewQuote.text)
                    .font(.system(size: 15))
                    .foregroundStyle(AppTheme.Colors.label)
                    .lineLimit(3)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(AppTheme.Colors.cardBackground.opacity(0.85))
            .clipShape(RoundedRectangle(cornerRadius: 20))
            .padding(.horizontal, 24)
            .accessibilityIdentifier("feed-notifications-reprompt-preview")

            Text(String(format: NSLocalizedString("growth_reminder_free_schedule", comment: ""), ReminderSchedule.slots(isPro: false).joined(separator: " · ")))
                .font(.system(size: 15, weight: .medium))
                .foregroundStyle(AppTheme.Colors.label)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)

            Spacer()

            Button {
                requestNotifications()
            } label: {
                if isRequesting {
                    ProgressView()
                        .tint(.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 56)
                        .background(AppTheme.Colors.accent)
                        .clipShape(RoundedRectangle(cornerRadius: 28))
                } else {
                    Text(String(localized: "onboarding_notifications_allow"))
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 56)
                        .background(AppTheme.Colors.accent)
                        .clipShape(RoundedRectangle(cornerRadius: 28))
                }
            }
            .disabled(isRequesting)
            .accessibilityIdentifier("feed-notifications-reprompt-allow")
            .padding(.horizontal, 24)

            Text(String(localized: "onboarding_notifications_optional_hint"))
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)

            Button {
                AnalyticsManager.shared.track(.notificationPermissionResult, properties: [
                    "source": "feed_reprompt",
                    "result": "skipped",
                ])
                finish()
            } label: {
                Text(String(localized: "growth_maybe_later"))
                    .font(.subheadline).foregroundStyle(AppTheme.Colors.secondaryLabel)
                    .frame(minHeight: 44)
            }
            .disabled(isRequesting)
            .accessibilityIdentifier("feed-notifications-reprompt-skip")
            .padding(.bottom, 24)
        }
        .background(AppBackground())
        .onAppear {
            if !hasTrackedPriming {
                hasTrackedPriming = true
                AnalyticsManager.shared.track(.notificationPrimingViewed, properties: [
                    "goal": appState.userProfile.goals.first ?? "unknown",
                    "quote_id": previewQuote.id,
                    "flow_id": "feed_reprompt",
                ])
            }
        }
    }

    private func requestNotifications() {
        guard !isRequesting else { return }
        isRequesting = true
        AnalyticsManager.shared.track(.notificationPermissionRequested, properties: ["source": "feed_reprompt"])
        Task {
            let granted = await NotificationScheduler.shared.requestAuthorization()
            await MainActor.run {
                isRequesting = false
                AnalyticsManager.shared.track(.notificationPermissionResult, properties: [
                    "source": "feed_reprompt",
                    "result": granted ? "allowed" : "denied",
                ])
                if granted {
                    // Remote-only notifications (v1.8.7): register for APNs
                    // now that permission is granted, same as onboarding.
                    UIApplication.shared.registerForRemoteNotifications()
                }
                finish()
            }
        }
    }
}
