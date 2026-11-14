import ComponentsKit
import SwiftUI
import UserNotifications
import UIKit

struct NotificationPermissionStepView: View {
    let next: () -> Void

    @EnvironmentObject private var appState: AppState
    @State private var notificationGranted = false
    @State private var notificationDenied = false
    @State private var isRequesting = false
    @State private var hasAttemptedPermission = false
    @State private var hasTrackedPriming = false

    /// Priming: システムダイアログの前に「実際に届く通知そのもの」を見せる。
    /// Phase 1 では planReveal で selector が選び、判断点として記録した
    /// その人の言葉をそのまま通知プレビューとして表示する。
    /// Phase 1 の回答が無い場合は従来の目標→quote 対応表へフォールバック。
    @State private var previewQuoteOverride: Quote?

    private var previewQuote: Quote {
        if let previewQuoteOverride { return previewQuoteOverride }
        let quoteIDs = ["self_love": "q013", "calm": "q021", "confidence": "q041", "letting_go": "q071"]
        let id = quoteIDs[appState.userProfile.goals.first ?? "self_love"] ?? "q013"
        return QuoteProvider.shared.byId(id, preferredLanguage: appState.effectiveLanguage)
            ?? QuoteProvider.shared.all(preferredLanguage: appState.effectiveLanguage)[0]
    }

    /// The schedule line shows the slots the user actually chose in the
    /// previous step; the fixed free schedule is only a fallback.
    private var scheduleText: String {
        let chosen = appState.personalizationProfile.nudgeSlots.sorted().map { $0.label }
        if !chosen.isEmpty {
            return String(format: NSLocalizedString("growth_chosen_schedule", comment: ""), chosen.joined(separator: " · "))
        }
        return String(format: NSLocalizedString("growth_reminder_free_schedule", comment: ""), ReminderSchedule.slots(isPro: false).joined(separator: " · "))
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

            // Priming: ロック画面に届く通知の実物プレビュー (自分の目標の言葉) と、
            // 実際に届く時刻を見せてから許可を聞く。
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
            .accessibilityIdentifier("onboarding-notifications-preview")

            Text(scheduleText)
                .font(.system(size: 15, weight: .medium))
                .foregroundStyle(AppTheme.Colors.label)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)

            Spacer()

            Button {
                if hasAttemptedPermission {
                    next()
                } else {
                    requestNotifications()
                }
            } label: {
                if isRequesting {
                    ProgressView()
                        .tint(.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 56)
                        .background(AppTheme.Colors.accent)
                        .clipShape(RoundedRectangle(cornerRadius: 28))
                } else {
                    Text(hasAttemptedPermission ? String(localized: "common_continue") : String(localized: "onboarding_notifications_allow"))
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 56)
                        .background(hasAttemptedPermission ? AppTheme.Colors.buttonSelected : AppTheme.Colors.accent)
                        .clipShape(RoundedRectangle(cornerRadius: 28))
                }
            }
            .disabled(isRequesting)
            .accessibilityIdentifier("onboarding-notifications-allow")
            .padding(.horizontal, 24)

            Text(String(localized: "onboarding_notifications_optional_hint"))
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)

            Button {
                AnalyticsManager.shared.track(.notificationPermissionResult, properties: ["result": "skipped"])
                next()
            } label: {
                Text(String(localized: "growth_maybe_later"))
                    .font(.subheadline).foregroundStyle(AppTheme.Colors.secondaryLabel)
                    .frame(minHeight: 44)
            }
            .disabled(isRequesting)
            .accessibilityIdentifier("onboarding-notifications-skip")
            .padding(.bottom, 24)
        }
        .background(AppBackground())
        .onAppear {
            if previewQuoteOverride == nil,
               let lastDecision = DecisionPointStore.shared.allRecords().last(where: { $0.recordKind == "decision" && $0.source == "onboarding_preview" }),
               let messageId = lastDecision.messageId {
                previewQuoteOverride = QuoteProvider.shared.byId(messageId, preferredLanguage: appState.effectiveLanguage)
            }
            if !hasTrackedPriming {
                hasTrackedPriming = true
                AnalyticsManager.shared.track(.notificationPrimingViewed, properties: [
                    "goal": appState.userProfile.goals.first ?? "unknown",
                    "quote_id": previewQuote.id,
                    "flow_id": "onboarding",
                ])
            }
            Task { await refreshAuthorizationState(autoAdvance: false) }
        }
    }

    private func requestNotifications() {
        guard !isRequesting else { return }
        isRequesting = true
        AnalyticsManager.shared.track(.notificationPermissionRequested, properties: ["source": "onboarding"])
        Task {
            let granted = await NotificationScheduler.shared.requestAuthorization()
            await MainActor.run {
                notificationGranted = granted
                notificationDenied = !granted
                isRequesting = false
                hasAttemptedPermission = true
                AnalyticsManager.shared.track(.notificationPermissionResult, properties: [
                    "source": "onboarding",
                    "result": granted ? "allowed" : "denied",
                ])
                if granted {
                    // v1.8.7: notifications are remote-only (APNs). Register now that
                    // the user granted permission so the device token reaches the backend.
                    UIApplication.shared.registerForRemoteNotifications()
                }
                next()
            }
        }
    }

    private func refreshAuthorizationState(autoAdvance: Bool) async {
        let settings = await UNUserNotificationCenter.current().notificationSettings()
        await MainActor.run {
            let authorized = settings.authorizationStatus == .authorized
                || settings.authorizationStatus == .provisional
                || settings.authorizationStatus == .ephemeral
            let timeSensitiveOk = settings.timeSensitiveSetting != .disabled
            notificationGranted = authorized && timeSensitiveOk
            notificationDenied = settings.authorizationStatus == .denied
        }
    }

    private func openSettings() {
        guard let url = URL(string: UIApplication.openSettingsURLString) else { return }
        UIApplication.shared.open(url)
    }
}
