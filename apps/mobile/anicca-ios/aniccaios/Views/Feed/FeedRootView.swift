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
    @State private var navigationRevision = 0
    @State private var lastTrackedQuoteID: String?
    private let recentQuotesKey = "anicca.feed.recent-quote-ids"
    /// Unique affirmations seen this launch — used as a lightweight "session finished" signal.
    @State private var viewedQuoteIDsThisSession: Set<String> = []
    @State private var didRequestReviewForSession = false
    @State private var showNotificationPriming = false
    @State private var didEvaluateNotificationReprompt = false

    /// Apple のお支払い更新ページ。RevenueCat の managementURL があればそれを優先。
    private var managePaymentURL: URL {
        appState.subscriptionInfo.managementURL
            ?? URL(string: "https://apps.apple.com/account/subscriptions")!
    }

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .top) {
                // Vertical paging — each page is forced to screen width.
                VerticalPager(count: quotes.count, currentIndex: $currentIndex, navigationRevision: navigationRevision) { idx in
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
                            Text(NSLocalizedString("growth_category_\(selectedCategory ?? "personalized")", comment: ""))
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
            .frame(width: geo.size.width, height: geo.size.height)
            .background {
                ZStack {
                    themeStore.image.resizable().scaledToFill()
                        .frame(width: geo.size.width, height: geo.size.height + geo.safeAreaInsets.top + geo.safeAreaInsets.bottom)
                        .clipped()
                    LinearGradient(colors: [.black.opacity(0.12), .clear, .black.opacity(0.28)], startPoint: .top, endPoint: .bottom)
                }
                .ignoresSafeArea()
                .allowsHitTesting(false)
                .accessibilityHidden(true)
            }
        }
        .environmentObject(themeStore)
        .environmentObject(likedStore)
        .analyticsScreen(.feed, flowID: "feed")
        .onAppear {
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
        .onChange(of: showCollections) { isPresented in
            if isPresented {
                AnalyticsManager.shared.trackScreenViewed(screenID: .feedCollections, flowID: "feed")
            } else {
                AnalyticsManager.shared.trackScreenViewedIfNeeded(screenID: .feed, flowID: "feed")
            }
        }
        .onChange(of: currentIndex) { _ in
            recordViewedQuoteIfNeeded()
            appendQuotesIfNeeded()
        }
        .confirmationDialog(String(localized: "growth_collections"), isPresented: $showCollections, titleVisibility: .visible) {
            Button(String(localized: "growth_category_personalized")) { selectedCategory = nil; rebuildFeed() }
            ForEach(Array(Set(QuoteProvider.shared.all(preferredLanguage: appState.effectiveLanguage).map(\.categoryID))).sorted(), id: \.self) { category in
                Button(NSLocalizedString("growth_category_\(category)", comment: "")) {
                    selectedCategory = category
                    rebuildFeed()
                }
            }
        }
        .sheet(isPresented: $showSaved, onDismiss: {
            AnalyticsManager.shared.trackScreenViewedIfNeeded(screenID: .feed, flowID: "feed")
        }) {
            NavigationStack {
                LikedQuotesView().environmentObject(likedStore)
                    .analyticsScreen(.feedSaved, flowID: "feed")
                    .toolbar { ToolbarItem(placement: .navigationBarTrailing) { Button(String(localized: "common_close")) { showSaved = false } } }
            }
        }
        .sheet(isPresented: $showReminders, onDismiss: {
            AnalyticsManager.shared.trackScreenViewedIfNeeded(screenID: .feed, flowID: "feed")
        }) {
            NavigationStack {
                NotificationsSettingsView()
                    .analyticsScreen(.feedReminders, flowID: "feed")
                    .toolbar { ToolbarItem(placement: .navigationBarTrailing) { Button(String(localized: "common_close")) { showReminders = false } } }
            }
        }
        .sheet(isPresented: $showThemes, onDismiss: {
            AnalyticsManager.shared.trackScreenViewedIfNeeded(screenID: .feed, flowID: "feed")
        }) {
            NavigationStack {
                ThemePickerView().environmentObject(themeStore)
                    .analyticsScreen(.feedThemes, flowID: "feed")
                    .toolbar { ToolbarItem(placement: .navigationBarTrailing) { Button(String(localized: "common_close")) { showThemes = false } } }
            }
        }
        .sheet(isPresented: $showNotificationPriming, onDismiss: {
            AnalyticsManager.shared.trackScreenViewedIfNeeded(screenID: .feed, flowID: "feed")
        }) {
            NotificationPrimingSheetView {
                showNotificationPriming = false
            }
        }
        .sheet(isPresented: $showSettings, onDismiss: {
            AnalyticsManager.shared.trackScreenViewedIfNeeded(screenID: .feed, flowID: "feed")
        }) {
            if #available(iOS 16.0, *) {
                NavigationStack {
                    SettingsSheet()
                        .analyticsScreen(.feedSettings, flowID: "feed")
                        .environmentObject(themeStore)
                        .environmentObject(likedStore)
                }
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
            } else {
                NavigationView {
                    SettingsSheet()
                        .analyticsScreen(.feedSettings, flowID: "feed")
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
        let destination = quoteNavigation.feedDestination(for: quote, in: quotes)
        quotes = destination.quotes
        navigationRevision += 1
        currentIndex = destination.index
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
        guard viewedQuoteIDsThisSession.count >= 3 else { return }
        if !didRequestReviewForSession {
            didRequestReviewForSession = true
            let reviewAsked = ReviewPromptCoordinator.shared.requestReviewIfAppropriate {
                requestReview()
            }
            // One ask per value moment: when the review prompt fired, the
            // notification re-ask waits for a later session.
            if reviewAsked { return }
        }
        evaluateNotificationRepromptIfNeeded()
    }

    /// Second-chance notification priming at the same value moment
    /// (3 affirmations read this session). Eligibility — return visit,
    /// attempt cap, cooldown, still .notDetermined — lives in
    /// `NotificationPrimingCoordinator` (anicca-ops Issue #48).
    private func evaluateNotificationRepromptIfNeeded() {
        guard !didEvaluateNotificationReprompt else { return }
        didEvaluateNotificationReprompt = true
        Task { @MainActor in
            guard await NotificationPrimingCoordinator.shared.shouldOfferReprompt() else { return }
            NotificationPrimingCoordinator.shared.recordRepromptShown()
            showNotificationPriming = true
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
            problems: selectedCategory == nil ? appState.userProfile.problems : [],
            likedIDs: likedStore.likedIds,
            recentIDs: UserDefaults.standard.stringArray(forKey: recentQuotesKey) ?? []
        )
    }

    private func rebuildFeed() {
        // Personalization measurement (1.9.10): record which onboarding
        // branch actually steered this feed, so the effect is visible in
        // Mixpanel next to affirmation_viewed (which carries category).
        if selectedCategory == nil {
            let problems = appState.userProfile.problems
            let categories = problems.flatMap { QuoteProvider.problemCategories[$0] ?? [] }
            if !categories.isEmpty {
                AnalyticsManager.shared.track(.personalizationApplied, properties: [
                    "problems": problems.joined(separator: ","),
                    "categories": Array(Set(categories)).sorted().joined(separator: ",")
                ])
            }
        }
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
