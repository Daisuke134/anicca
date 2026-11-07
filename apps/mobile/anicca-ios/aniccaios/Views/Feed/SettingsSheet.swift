import SwiftUI
import UIKit
import UserNotifications
import OSLog
import Combine
import RevenueCat
import RevenueCatUI

/// ↓ pull-down sheet from FeedRootView.
/// 1mm clone of i.am app settings (modal sheet with categories: Theme / Notifications / Saved / Liked / Subscription / Account / Sign out).
struct SettingsSheet: View {
    @EnvironmentObject var themeStore: ThemeStore
    @EnvironmentObject var likedStore: LikedQuotesStore
    @Environment(\.dismiss) private var dismiss

    @State private var showThemePicker = false
    @State private var showSavedQuotes = false
    @State private var showLikedQuotes = false
    @State private var showSignOutConfirmation = false
    @State private var showPurchasePlans = false

    var body: some View {
        List {
            Section {
                NavigationLink {
                    ThemePickerView()
                        .environmentObject(themeStore)
                        .analyticsScreen(.feedThemes, flowID: "feed")
                } label: {
                    HStack {
                        Label(String(localized: "settings_theme"), systemImage: "paintpalette")
                        Spacer()
                        Text(themeStore.selected.displayName)
                            .foregroundStyle(.secondary)
                    }
                }
                .accessibilityIdentifier("settings-theme")

                NavigationLink {
                    NotificationsSettingsView()
                        .analyticsScreen(.feedReminders, flowID: "feed")
                } label: {
                    Label(String(localized: "settings_notifications"), systemImage: "bell")
                }

                NavigationLink {
                    LikedQuotesView()
                        .environmentObject(likedStore)
                        .analyticsScreen(.feedSaved, flowID: "feed")
                } label: {
                    HStack {
                        Label(String(localized: "settings_liked_quotes"), systemImage: "heart")
                        Spacer()
                        Text("\(likedStore.likedIds.count)")
                            .foregroundStyle(.secondary)
                    }
                }
            }

            Section {
                Button {
                    showPurchasePlans = true
                } label: {
                    Label(String(localized: "settings_subscription_subscribe"), systemImage: "star.circle")
                }
                .accessibilityIdentifier("settings-subscribe")

                NavigationLink {
                    RevenueCatUI.CustomerCenterView()
                        .navigationTitle(String(localized: "settings_subscription"))
                        .navigationBarTitleDisplayMode(.inline)
                        .analyticsScreen(.settingsSubscription, flowID: "settings")
                } label: {
                    Label(String(localized: "settings_subscription"), systemImage: "creditcard")
                }
            }

            Section {
                Button(role: .destructive) {
                    showSignOutConfirmation = true
                } label: {
                    Label(String(localized: "settings_sign_out"), systemImage: "rectangle.portrait.and.arrow.right")
                }
            }
        }
        .listStyle(.insetGrouped)
        .navigationTitle(String(localized: "settings_title"))
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button(String(localized: "common_done")) { dismiss() }
            }
        }
        .fullScreenCover(isPresented: $showPurchasePlans) {
            PaywallFlowContainer(
                onPurchaseSuccess: { customerInfo in
                    AppState.shared.updateSubscriptionInfo(from: customerInfo)
                    showPurchasePlans = false
                    AnalyticsManager.shared.trackScreenViewedIfNeeded(screenID: .feedSettings, flowID: "feed")
                },
                onDismiss: {
                    showPurchasePlans = false
                    AnalyticsManager.shared.trackScreenViewedIfNeeded(screenID: .feedSettings, flowID: "feed")
                },
                flowID: "settings_subscription"
            )
            .environmentObject(AppState.shared)
        }
        .confirmationDialog(String(localized: "settings_sign_out"), isPresented: $showSignOutConfirmation, titleVisibility: .visible) {
            Button(String(localized: "common_sign_out"), role: .destructive) {
                AppState.shared.signOutPreservingSensorAccess()
                dismiss()
            }
            Button(String(localized: "common_cancel"), role: .cancel) {}
        }
    }
}

/// 8 theme grid. Tap = select + persist + dismiss.
struct ThemePickerView: View {
    @EnvironmentObject var themeStore: ThemeStore
    @Environment(\.dismiss) private var dismiss

    private let columns = [GridItem(.flexible()), GridItem(.flexible())]

    var body: some View {
        ScrollView {
            LazyVGrid(columns: columns, spacing: 16) {
                ForEach(ThemeID.allCases) { theme in
                    Button {
                        themeStore.select(theme)
                        dismiss()
                    } label: {
                        ZStack(alignment: .bottomLeading) {
                            theme.image
                                .resizable()
                                .scaledToFill()
                                .frame(height: 240)
                                .clipped()
                                .clipShape(RoundedRectangle(cornerRadius: 16))
                            HStack {
                                Text(theme.displayName)
                                    .font(.footnote)
                                    .foregroundStyle(.white)
                                    .padding(8)
                                Spacer()
                                if themeStore.selected == theme {
                                    Image(systemName: "checkmark.circle.fill")
                                        .foregroundStyle(.white)
                                        .padding(8)
                                }
                            }
                            .background(LinearGradient(colors: [.clear, .black.opacity(0.5)], startPoint: .top, endPoint: .bottom))
                            .clipShape(RoundedRectangle(cornerRadius: 16))
                        }
                        .accessibilityIdentifier("theme-\(theme.rawValue)")
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(16)
        }
        .navigationTitle(String(localized: "settings_theme"))
        .navigationBarTitleDisplayMode(.inline)
    }
}

/// Liked quotes grid. Tap = (future) jump back to feed at that quote.
struct LikedQuotesView: View {
    @EnvironmentObject var likedStore: LikedQuotesStore

    var likedQuotes: [Quote] {
        likedStore.savedQuotes(in: QuoteProvider.shared.all())
    }

    var body: some View {
        Group {
            if likedQuotes.isEmpty {
                VStack(spacing: 16) {
                    Image(systemName: "heart")
                        .font(.system(size: 44))
                        .foregroundStyle(.secondary)
                    Text(String(localized: "liked_empty_title"))
                        .font(.headline)
                    Text(String(localized: "liked_empty_subtitle"))
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                }
                .padding(40)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                List {
                    ForEach(likedQuotes) { q in
                        Text(q.text)
                            .padding(.vertical, 8)
                    }
                }
            }
        }
        .navigationTitle(String(localized: "settings_liked_quotes"))
        .navigationBarTitleDisplayMode(.inline)
    }
}

/// Shows the actual server schedule and OS permission separately.
struct NotificationsSettingsView: View {
    @ObservedObject private var appState = AppState.shared
    @Environment(\.openURL) private var openURL
    @Environment(\.scenePhase) private var scenePhase
    @State private var notificationsAllowed = false
    @State private var isUpdatingPermission = false
    private let permissionLogger = Logger(subsystem: "com.anicca.ios", category: "NotificationSettings")

    private var slots: [String] { ReminderSchedule.slots(isPro: appState.subscriptionInfo.isEntitled) }

    var body: some View {
        Form {
            Section {
                HStack {
                    Text(String(localized: "notifications_daily_count"))
                    Spacer()
                    Text("\(slots.count)")
                        .foregroundStyle(.secondary)
                }
                ForEach(slots, id: \.self) { time in Text(time).monospacedDigit() }
                Text(TimeZone.current.identifier).font(.footnote).foregroundStyle(.secondary)
                Text(String(localized: notificationsAllowed ? "growth_notifications_on" : "growth_notifications_off"))
                    .accessibilityIdentifier("reminder-permission-status")
                Button(String(localized: "growth_notification_settings")) {
                    permissionLogger.notice("permission tap busy=\(isUpdatingPermission, privacy: .public)")
                    guard !isUpdatingPermission else { return }
                    isUpdatingPermission = true
                    Task { @MainActor in
                        defer { isUpdatingPermission = false }
                        let settings = await UNUserNotificationCenter.current().notificationSettings()
                        permissionLogger.notice("permission prior status=\(settings.authorizationStatus.rawValue, privacy: .public)")
                        if settings.authorizationStatus == .notDetermined {
                            AnalyticsManager.shared.track(.notificationPermissionRequested, properties: ["source": "settings"])
                            _ = await NotificationScheduler.shared.requestAuthorizationIfNeeded()
                            notificationsAllowed = await NotificationScheduler.shared.isAuthorizedForAlerts()
                            permissionLogger.notice("permission prompt completed alerts=\(notificationsAllowed, privacy: .public)")
                            AnalyticsManager.shared.track(.notificationPermissionResult, properties: ["source": "settings", "result": notificationsAllowed ? "allowed" : "denied"])
                            if notificationsAllowed { UIApplication.shared.registerForRemoteNotifications() }
                            // A permission choice finishes here. Opening Settings is
                            // a separate, explicit action after permission is settled.
                            return
                        }
                        permissionLogger.notice("permission opening system settings")
                        if let url = URL(string: UIApplication.openSettingsURLString) { openURL(url) }
                    }
                }
                .disabled(isUpdatingPermission)
                .accessibilityIdentifier("reminder-enable-notifications")
            } footer: {
                Text(String(localized: "growth_reminder_explanation"))
            }
        }
        .navigationTitle(String(localized: "settings_notifications"))
        .navigationBarTitleDisplayMode(.inline)
        .task { notificationsAllowed = await NotificationScheduler.shared.isAuthorizedForAlerts() }
        .onChange(of: scenePhase) { phase in
            if phase == .active { Task { notificationsAllowed = await NotificationScheduler.shared.isAuthorizedForAlerts() } }
        }
    }
}
