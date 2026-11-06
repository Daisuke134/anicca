import SwiftUI
import Combine
import StoreKit
import UIKit

/// Anicca app root: full-bleed vertical paging feed.
/// Background = single theme image shared across ALL quotes. Swiping changes the quote text only.
/// Top chrome (hamburger + settings) is locked in place, never moves on swipe.
struct FeedRootView: View {
    @StateObject private var themeStore = ThemeStore()
    @StateObject private var likedStore = LikedQuotesStore()
    @ObservedObject private var appState = AppState.shared
    @StateObject private var quoteNavigation = QuoteNavigationCoordinator.shared
    @Environment(\.openURL) private var openURL
    @Environment(\.requestReview) private var requestReview
    @State private var quotes: [Quote] = []
    @State private var currentIndex: Int = 0
    @State private var showSettings = false
    @State private var showSaved = false
    @State private var showReminders = false
    @State private var showThemes = false
    @State private var showCollections = false
    @State private var selectedCategory: String?
    @State private var feedRevision = 0
    @State private var lastTrackedQuoteID: String?
    private let recentQuotesKey = "anicca.feed.recent-quote-ids"
    /// Unique affirmations seen this launch — used as a lightweight "session finished" signal.
    @State private var viewedQuoteIDsThisSession: Set<String> = []
    @State private var didRequestReviewForSession = false

    /// Apple のお支払い更新ページ。RevenueCat の managementURL があればそれを優先。
    private var managePaymentURL: URL {
        appState.subscriptionInfo.managementURL
            ?? URL(string: "https://apps.apple.com/account/subscriptions")!
    }

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .top) {
                // SHARED background (does NOT change across swipes).
                themeStore.image
                    .resizable()
                    .scaledToFill()
                    .frame(width: geo.size.width, height: geo.size.height + geo.safeAreaInsets.top + geo.safeAreaInsets.bottom)
                    .ignoresSafeArea()
                    .accessibilityHidden(true)

                LinearGradient(colors: [.black.opacity(0.12), .clear, .black.opacity(0.28)], startPoint: .top, endPoint: .bottom)
                    .ignoresSafeArea().accessibilityHidden(true)

                // Vertical paging — each page is forced to screen width.
                VerticalPager(count: quotes.count, currentIndex: $currentIndex) { idx in
                    QuoteCardView(quote: quotes[idx], pageWidth: geo.size.width)
                        .frame(width: geo.size.width, height: geo.size.height)
                        .environmentObject(themeStore)
                        .environmentObject(likedStore)
                }
                .id(feedRevision)
                .frame(width: geo.size.width, height: geo.size.height)
                .accessibilityIdentifier("feed-scroll")

                // Top chrome — single settings button pinned top-right.
                HStack {
                    Button { showCollections = true } label: {
                        HStack(spacing: 6) {
                            Text(String(localized: String.LocalizationValue("growth_category_\(selectedCategory ?? "personalized")")))
                            Image(systemName: "chevron.down").font(.caption2)
                        }
                        .font(.subheadline).foregroundStyle(.white)
                        .padding(.horizontal, 14).padding(.vertical, 12)
                        .background(.black.opacity(0.25), in: Capsule())
                    }
                    .accessibilityIdentifier("feed-collections")
                    Spacer()
                    chromeButton(systemName: "paintpalette", identifier: "feed-themes") { showThemes = true }
                    chromeButton(systemName: "slider.horizontal.3", identifier: "feed-settings") {
                        showSettings = true
                    }
                }
                .padding(.horizontal, 16)
                .padding(.top, 8)
                .zIndex(10)

                VStack {
                    Spacer()
                    HStack {
                        feedAction("growth_daily", icon: "sun.max", id: "feed-daily") {
                            selectedCategory = nil
                            rebuildFeed()
                        }
                        Spacer()
                        feedAction("settings_liked_quotes", icon: "bookmark", id: "feed-saved") { showSaved = true }
                        Spacer()
                        feedAction("settings_notifications", icon: "bell", id: "feed-reminders") { showReminders = true }
                    }
                    .padding(.horizontal, 24).padding(.bottom, 12)
                }
                .allowsHitTesting(true)
                .zIndex(9)

                // Billing-issue recovery: Apple がカード課金に失敗(grace/retry)している時、
                // 支払い更新を促すバナーを出す。タップで Apple のお支払い管理ページへ。
                // (involuntary churn 回収 — Apple "Reducing Involuntary Subscriber Churn" 推奨)
                if appState.subscriptionInfo.hasBillingIssue {
                    billingIssueBanner
                        .padding(.horizontal, 16)
                        .padding(.top, 56)
                        .zIndex(11)
                        .transition(.move(edge: .top).combined(with: .opacity))
                }
            }
        }
        .environmentObject(themeStore)
        .environmentObject(likedStore)
        .onAppear {
            AnalyticsManager.shared.track(.screenViewed, properties: ["screen_id": "feed"])
            if quotes.isEmpty {
                rebuildFeed()
            }
            applyPendingQuoteNavigation()
            recordViewedQuoteIfNeeded()
        }
        .onChange(of: quoteNavigation.pendingRequest) { _ in
            applyPendingQuoteNavigation()
        }
        .onChange(of: quotes) { _ in
            applyPendingQuoteNavigation()
        }
        .onChange(of: currentIndex) { _ in
            recordViewedQuoteIfNeeded()
            appendQuotesIfNeeded()
        }
        .confirmationDialog(String(localized: "growth_collections"), isPresented: $showCollections, titleVisibility: .visible) {
            Button(String(localized: "growth_category_personalized")) { selectedCategory = nil; rebuildFeed() }
            ForEach(Array(Set(QuoteProvider.shared.all(preferredLanguage: appState.effectiveLanguage).map(\.categoryID))).sorted(), id: \.self) { category in
                Button(String(localized: String.LocalizationValue("growth_category_\(category)"))) {
                    selectedCategory = category
                    rebuildFeed()
                }
            }
        }
        .sheet(isPresented: $showSaved) {
            NavigationStack {
                LikedQuotesView().environmentObject(likedStore)
                    .onAppear { AnalyticsManager.shared.track(.screenViewed, properties: ["screen_id": "feed.saved"]) }
                    .toolbar { ToolbarItem(placement: .navigationBarTrailing) { Button(String(localized: "common_close")) { showSaved = false } } }
            }
        }
        .sheet(isPresented: $showReminders) {
            NavigationStack {
                NotificationsSettingsView()
                    .onAppear { AnalyticsManager.shared.track(.screenViewed, properties: ["screen_id": "feed.reminders"]) }
                    .toolbar { ToolbarItem(placement: .navigationBarTrailing) { Button(String(localized: "common_close")) { showReminders = false } } }
            }
        }
        .sheet(isPresented: $showThemes) {
            NavigationStack {
                ThemePickerView().environmentObject(themeStore)
                    .onAppear { AnalyticsManager.shared.track(.screenViewed, properties: ["screen_id": "feed.themes"]) }
                    .toolbar { ToolbarItem(placement: .navigationBarTrailing) { Button(String(localized: "common_close")) { showThemes = false } } }
            }
        }
        .sheet(isPresented: $showSettings) {
            if #available(iOS 16.0, *) {
                NavigationStack {
                    SettingsSheet()
                        .onAppear { AnalyticsManager.shared.track(.screenViewed, properties: ["screen_id": "feed.settings"]) }
                        .environmentObject(themeStore)
                        .environmentObject(likedStore)
                }
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
            } else {
                NavigationView {
                    SettingsSheet()
                        .environmentObject(themeStore)
                        .environmentObject(likedStore)
                }
                .navigationViewStyle(.stack)
            }
        }
    }

    private func applyPendingQuoteNavigation() {
        let catalog = QuoteProvider.shared.all(preferredLanguage: appState.effectiveLanguage)
        let catalogIDs = Set(catalog.map(\.id))
        guard let quote = quoteNavigation.resolveQuote(in: catalog + quotes.filter { !catalogIDs.contains($0.id) }) else { return }
        AnalyticsManager.shared.track(.notificationDestinationResolved, properties: ["quote_id": quote.id, "result": "displayed"])
        let index: Int
        if let existingIndex = quotes.firstIndex(where: { $0.id == quote.id }) {
            index = existingIndex
        } else {
            quotes.append(quote)
            index = quotes.count - 1
        }
        withAnimation { currentIndex = index }
    }

    /// After reading several affirmations in one launch, treat that as a finished session.
    private func recordViewedQuoteIfNeeded() {
        guard quotes.indices.contains(currentIndex) else { return }
        let quoteID = quotes[currentIndex].id
        if lastTrackedQuoteID != quoteID {
            lastTrackedQuoteID = quoteID
            AnalyticsManager.shared.track(.affirmationViewed, properties: ["quote_id": quoteID, "category": quotes[currentIndex].categoryID])
        }
        viewedQuoteIDsThisSession.insert(quoteID)
        var recent = UserDefaults.standard.stringArray(forKey: recentQuotesKey) ?? []
        recent.removeAll { $0 == quoteID }
        recent.append(quoteID)
        UserDefaults.standard.set(Array(recent.suffix(20)), forKey: recentQuotesKey)
        guard !didRequestReviewForSession, viewedQuoteIDsThisSession.count >= 3 else { return }
        didRequestReviewForSession = true
        ReviewPromptCoordinator.shared.requestReviewIfAppropriate {
            requestReview()
        }
    }

    private func nextQuotes(excludingQueued: Bool) -> [Quote] {
        let catalog = QuoteProvider.shared.all(preferredLanguage: appState.effectiveLanguage)
            .filter { selectedCategory == nil || $0.categoryID == selectedCategory }
        let queued = Set(quotes.map(\.id))
        let remaining = excludingQueued ? catalog.filter { !queued.contains($0.id) } : catalog
        return QuoteProvider.recommendations(
            from: remaining.isEmpty ? catalog : remaining,
            goals: selectedCategory.map { [$0] } ?? appState.userProfile.goals,
            likedIDs: likedStore.likedIds,
            recentIDs: UserDefaults.standard.stringArray(forKey: recentQuotesKey) ?? []
        )
    }

    private func rebuildFeed() {
        quotes = Array(nextQuotes(excludingQueued: false).prefix(8))
        currentIndex = 0
        feedRevision += 1
    }

    private func appendQuotesIfNeeded() {
        guard currentIndex >= quotes.count - 3 else { return }
        quotes.append(contentsOf: nextQuotes(excludingQueued: true).prefix(6))
    }

    private func feedAction(_ key: String, icon: String, id: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Label(String(localized: String.LocalizationValue(key)), systemImage: icon)
                .font(.caption).foregroundStyle(.white).frame(minHeight: 44)
        }.accessibilityIdentifier(id)
    }

    private var billingIssueBanner: some View {
        Button {
            openURL(managePaymentURL)
        } label: {
            HStack(spacing: 10) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(.white)
                VStack(alignment: .leading, spacing: 2) {
                    Text(String(localized: "billing_issue_title"))
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(.white)
                    Text(String(localized: "billing_issue_action"))
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(.white.opacity(0.85))
                }
                Spacer(minLength: 8)
                Image(systemName: "chevron.right")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(.white.opacity(0.85))
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Color(red: 0.78, green: 0.27, blue: 0.20))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .stroke(.white.opacity(0.18), lineWidth: 0.5)
            )
            .shadow(color: .black.opacity(0.3), radius: 8, y: 2)
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("billing-issue-banner")
    }

    @ViewBuilder
    private func chromeButton(systemName: String, identifier: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: systemName)
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(.white)
                .frame(width: 40, height: 40)
                .background(
                    Circle()
                        .fill(.black.opacity(0.45))
                )
                .overlay(
                    Circle()
                        .stroke(.white.opacity(0.25), lineWidth: 0.5)
                )
                .contentShape(Circle())
                .shadow(color: .black.opacity(0.4), radius: 8, y: 2)
        }
        .accessibilityIdentifier(identifier)
    }
}
