import SwiftUI
import StoreKit

/// How a home card stopped being on screen. Recorded with every display so
/// the eval can separate "the words moved on by themselves" from "the
/// person moved on" and from "the app went away".
enum HomeDisplayEndCause: String {
    case userSwipe
    case autoAdvance
    case notificationJump
    case appClosed
    case replaced
}

/// One card in the living-home deck.
struct HomeDeckCard: Identifiable {
    enum Origin: String {
        /// The intervention the Manager chose for this person today.
        case selectedIntervention
        /// A further word from the same ranked candidate list, explored by
        /// swiping or by the home advancing on its own.
        case exploration
        /// The words a tapped notification delivered.
        case notification
    }

    let quote: Quote
    var origin: Origin
    var deliveryId: String?

    var id: String { quote.id }
}

/// The deck behind the living home. Published so a card already on screen
/// picks up the delivery id its display records, without waiting for the
/// pager to rebuild the page.
final class HomeDeckModel: ObservableObject {
    @Published var cards: [HomeDeckCard] = []
    /// Size of the ranked candidate list the deck was built from; the
    /// assignment probability of an explored card is 1 / candidateCount.
    var candidateCount: Int = 1
}

/// Idle auto-advance for the living home. The interval is provisional: the
/// living-home research (anicca-ops `files/home-living-ux-research-2026-11-15.md`)
/// records that no source fixes the number, so it is an eval decision to
/// make later, not a design constant.
enum HomeAutoAdvance {
    static let interval: TimeInterval = 8

    static func shouldAdvance(
        now: Date,
        lastInteractionAt: Date,
        isSceneActive: Bool,
        cardCount: Int,
        anySheetPresented: Bool,
        interval: TimeInterval = HomeAutoAdvance.interval
    ) -> Bool {
        guard isSceneActive, cardCount > 1, !anySheetPresented else { return false }
        return now.timeIntervalSince(lastInteractionAt) >= interval
    }

    static func nextIndex(current: Int, count: Int) -> Int {
        guard count > 0 else { return 0 }
        return (current + 1) % count
    }
}

/// Living home. The first card is the intervention the Manager chose for
/// this person today — the words they have wanted to hear. Behind it sits a
/// swipeable deck of further words from the same ranking. Left untouched,
/// the words keep changing on their own; any touch hands control to the
/// person. Every displayed word is recorded — quote, origin, display time,
/// dwell, and how the display ended — as a ManagerBench intervention case.
struct FeedRootView: View {
    @StateObject private var themeStore = ThemeStore()
    @StateObject private var likedStore = LikedQuotesStore()
    @StateObject private var deckModel = HomeDeckModel()
    @ObservedObject private var appState = AppState.shared
    @StateObject private var quoteNavigation = QuoteNavigationCoordinator.shared
    @Environment(\.openURL) private var openURL
    @Environment(\.scenePhase) private var scenePhase
    @State private var currentIndex: Int = 0
    @State private var navigationRevision: Int = 0
    @State private var displayedIndex: Int?
    @State private var displayedAt: Date?
    @State private var lastInteractionAt: Date = Date()
    @State private var pendingEndCause: HomeDisplayEndCause = .userSwipe
    @State private var backgroundDrift = false
    @State private var showSettings = false
    @State private var showSaved = false
    @State private var showReminders = false
    @State private var showThemes = false
    @State private var lastTrackedQuoteID: String?

    private let autoAdvanceTimer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    private var managePaymentURL: URL {
        appState.subscriptionInfo.managementURL
            ?? URL(string: "https://apps.apple.com/account/subscriptions")!
    }

    private var anySheetPresented: Bool {
        showSettings || showSaved || showReminders || showThemes
    }

    var body: some View {
        GeometryReader { geo in
            VStack(spacing: 16) {
                HStack {
                    Text(String(localized: "growth_today_for_you"))
                        .font(.system(.title2, design: .serif))
                        .fixedSize(horizontal: false, vertical: true)
                        .foregroundStyle(themeStore.selected.foregroundColor)
                        .accessibilityAddTraits(.isHeader)
                    Spacer(minLength: 8)
                    chromeButton(systemName: "paintpalette", identifier: "feed-themes") { showThemes = true }
                    chromeButton(systemName: "slider.horizontal.3", identifier: "feed-settings") { showSettings = true }
                }
                .padding(.horizontal, 24)
                .padding(.top, 8)

                if appState.subscriptionInfo.hasBillingIssue {
                    billingIssueBanner.padding(.horizontal, 24)
                }

                GeometryReader { contentGeometry in
                    if !deckModel.cards.isEmpty {
                        VerticalPager(count: deckModel.cards.count, currentIndex: $currentIndex, navigationRevision: navigationRevision) { index in
                            HomeDeckPage(model: deckModel, index: index, pageWidth: geo.size.width)
                                .frame(width: contentGeometry.size.width, height: contentGeometry.size.height)
                                .environmentObject(themeStore)
                                .environmentObject(likedStore)
                        }
                        .accessibilityIdentifier("feed-today")
                    }
                }

                HStack {
                    feedAction("growth_daily", icon: "sun.max", id: "feed-daily") { returnToTodaysWords() }
                    Spacer(minLength: 8)
                    feedAction("settings_liked_quotes", icon: "heart", id: "feed-saved") { showSaved = true }
                    Spacer(minLength: 8)
                    feedAction("settings_notifications", icon: "bell", id: "feed-reminders") { showReminders = true }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 4)
                .background(AppTheme.Colors.cardBackground.opacity(0.94), in: RoundedRectangle(cornerRadius: 18))
                .padding(.horizontal, 16)
                .padding(.bottom, 12)
            }
            .background {
                // The background itself is alive: a slow drift under the
                // words, free with SwiftUI alone.
                themeStore.image.resizable().scaledToFill()
                    .frame(width: geo.size.width, height: geo.size.height + geo.safeAreaInsets.top + geo.safeAreaInsets.bottom)
                    .scaleEffect(backgroundDrift ? 1.09 : 1.02)
                    .offset(x: backgroundDrift ? -12 : 12)
                    .animation(.easeInOut(duration: 26).repeatForever(autoreverses: true), value: backgroundDrift)
                    .clipped()
                    .ignoresSafeArea()
                    .accessibilityHidden(true)
            }
        }
        .environmentObject(themeStore)
        .environmentObject(likedStore)
        .analyticsScreen(.feed, flowID: "feed")
        .onAppear {
            backgroundDrift = true
            refreshToday()
        }
        .onReceive(autoAdvanceTimer) { now in
            guard HomeAutoAdvance.shouldAdvance(
                now: now,
                lastInteractionAt: lastInteractionAt,
                isSceneActive: scenePhase == .active,
                cardCount: deckModel.cards.count,
                anySheetPresented: anySheetPresented
            ) else { return }
            pendingEndCause = .autoAdvance
            withAnimation(.easeInOut(duration: 0.6)) {
                currentIndex = HomeAutoAdvance.nextIndex(current: currentIndex, count: deckModel.cards.count)
            }
        }
        .onChange(of: currentIndex) { newIndex in
            handleIndexChange(to: newIndex)
        }
        .onChange(of: scenePhase) { phase in
            switch phase {
            case .active:
                lastInteractionAt = Date()
                refreshToday()
                if displayedIndex == nil, !deckModel.cards.isEmpty {
                    beginDisplay(at: currentIndex)
                }
            case .background:
                endDisplay(cause: .appClosed)
            default:
                break
            }
        }
        .onChange(of: appState.effectiveLanguage) { _ in refreshToday() }
        .onChange(of: quoteNavigation.pendingRequest) { _ in applyPendingQuoteNavigation() }
        .sheet(isPresented: $showSaved, onDismiss: sheetDismissed) {
            NavigationStack {
                LikedQuotesView().environmentObject(likedStore)
                    .analyticsScreen(.feedSaved, flowID: "feed")
                    .toolbar { ToolbarItem(placement: .navigationBarTrailing) { Button(String(localized: "common_close")) { showSaved = false } } }
            }
        }
        .sheet(isPresented: $showReminders, onDismiss: sheetDismissed) {
            NavigationStack {
                NotificationsSettingsView()
                    .analyticsScreen(.feedReminders, flowID: "feed")
                    .toolbar { ToolbarItem(placement: .navigationBarTrailing) { Button(String(localized: "common_close")) { showReminders = false } } }
            }
        }
        .sheet(isPresented: $showThemes, onDismiss: sheetDismissed) {
            NavigationStack {
                ThemePickerView().environmentObject(themeStore)
                    .analyticsScreen(.feedThemes, flowID: "feed")
                    .toolbar { ToolbarItem(placement: .navigationBarTrailing) { Button(String(localized: "common_close")) { showThemes = false } } }
            }
        }
        .sheet(isPresented: $showSettings, onDismiss: sheetDismissed) {
            NavigationStack {
                SettingsSheet()
                    .analyticsScreen(.feedSettings, flowID: "feed")
                    .environmentObject(themeStore)
                    .environmentObject(likedStore)
            }
            .presentationDetents([.large])
            .presentationDragIndicator(.visible)
        }
    }

    private func recordHomeScreen() {
        AnalyticsManager.shared.trackScreenViewedIfNeeded(screenID: .feed, flowID: "feed")
    }

    private func sheetDismissed() {
        // Reading a sheet is interaction: the words wait a full idle
        // interval again before they start moving on their own.
        lastInteractionAt = Date()
        recordHomeScreen()
    }

    private func returnToTodaysWords() {
        lastInteractionAt = Date()
        guard currentIndex != 0, !deckModel.cards.isEmpty else { return }
        pendingEndCause = .userSwipe
        withAnimation(.easeInOut(duration: 0.35)) { currentIndex = 0 }
    }

    private func refreshToday() {
        let now = Date()
        appState.refreshSyntheticUserIfNeeded(now: now)
        let language = appState.effectiveLanguage
        let presentation = DailyAffirmationStore.shared.todayAffirmation(language: language.rawValue, now: now) {
            let user = appState.syntheticUser
            let catalog = QuoteProvider.shared.all(preferredLanguage: language)
            let band = PersonalizedNudgeSelector.TimeBand.band(forHour: Calendar.current.component(.hour, from: now))
            guard let selection = PersonalizedNudgeSelector.select(
                user: user, pool: catalog,
                shownAt: user.shownTimestamps, now: now, band: band
            ) else { return catalog.first.map { .init(quote: $0, deliveryId: nil) } }
            let origin = DecisionPointRecorder.shared.recordDecision(selection: selection, syntheticUser: user, source: "daily_home")
            return .init(quote: selection.quote, deliveryId: origin)
        }
        if let presentation, deckModel.cards.first?.quote.id != presentation.quote.id {
            buildDeck(selected: presentation, language: language, now: now)
        }
        applyPendingQuoteNavigation()
    }

    /// Deck order: today's chosen intervention first, then the selector's
    /// ranked candidates in rank order.
    private func buildDeck(selected presentation: DailyAffirmationStore.Presentation, language: LanguagePreference, now: Date, firstOrigin: HomeDeckCard.Origin = .selectedIntervention) {
        endDisplay(cause: .replaced)
        let user = appState.syntheticUser
        let catalog = QuoteProvider.shared.all(preferredLanguage: language)
        let band = PersonalizedNudgeSelector.TimeBand.band(forHour: Calendar.current.component(.hour, from: now))
        let ranked = PersonalizedNudgeSelector.rankedCandidates(
            user: user, pool: catalog,
            shownAt: user.shownTimestamps, now: now, band: band
        )
        deckModel.candidateCount = max(ranked.count, 1)
        var cards = [HomeDeckCard(quote: presentation.quote, origin: firstOrigin, deliveryId: presentation.deliveryId)]
        for quote in ranked where quote.id != presentation.quote.id {
            cards.append(HomeDeckCard(quote: quote, origin: .exploration, deliveryId: nil))
            if cards.count >= 12 { break }
        }
        deckModel.cards = cards
        currentIndex = 0
        navigationRevision += 1
        lastInteractionAt = Date()
        beginDisplay(at: 0)
    }

    private func applyPendingQuoteNavigation() {
        var catalog = QuoteProvider.shared.all(preferredLanguage: appState.effectiveLanguage)
        if let first = deckModel.cards.first, !catalog.contains(where: { $0.id == first.quote.id }) {
            catalog.append(first.quote)
        }
        let notificationDeliveryId = quoteNavigation.pendingRequest?.deliveryId
        guard let destination = quoteNavigation.resolveQuote(in: catalog) else { return }
        DailyAffirmationStore.shared.seed(destination, language: appState.effectiveLanguage.rawValue, deliveryId: notificationDeliveryId)
        AnalyticsManager.shared.track(.notificationDestinationResolved, properties: ["quote_id": destination.id, "result": "displayed"])
        buildDeck(
            selected: .init(quote: destination, deliveryId: notificationDeliveryId),
            language: appState.effectiveLanguage,
            now: Date(),
            firstOrigin: .notification
        )
        navigationRevision += 1
    }

    // MARK: - Display recording

    private func handleIndexChange(to newIndex: Int) {
        lastInteractionAt = Date()
        guard displayedIndex != newIndex else { return }
        endDisplay(cause: pendingEndCause)
        pendingEndCause = .userSwipe
        beginDisplay(at: newIndex)
    }

    private func beginDisplay(at index: Int) {
        guard deckModel.cards.indices.contains(index), displayedIndex != index else { return }
        displayedIndex = index
        displayedAt = Date()
        // An explored word becomes an intervention case the moment it is
        // actually displayed — never before — with the uniform probability
        // of its position in the ranked candidate list.
        if deckModel.cards[index].origin == .exploration, deckModel.cards[index].deliveryId == nil {
            let card = deckModel.cards[index]
            let selection = PersonalizedNudgeSelector.Selection(
                quote: card.quote,
                reason: "home_deck_exploration",
                candidateCount: deckModel.candidateCount,
                assignedProbability: 1.0 / Double(deckModel.candidateCount),
                policyVersion: PersonalizedNudgeSelector.policyVersion
            )
            deckModel.cards[index].deliveryId = DecisionPointRecorder.shared.recordDecision(
                selection: selection, syntheticUser: appState.syntheticUser, source: "home_deck"
            )
        }
        recordViewedQuoteIfNeeded(at: index)
    }

    private func endDisplay(cause: HomeDisplayEndCause) {
        guard let index = displayedIndex, let startedAt = displayedAt,
              deckModel.cards.indices.contains(index) else {
            displayedIndex = nil
            displayedAt = nil
            return
        }
        let card = deckModel.cards[index]
        let dwell = Date().timeIntervalSince(startedAt)
        // Swiping past a word without saving it is the "not for me" signal.
        // A saved word already recorded its own response at tap time.
        if cause == .userSwipe, !likedStore.isLiked(card.quote.id) {
            DecisionPointRecorder.shared.recordQuoteResponse(
                messageId: card.quote.id, deliveryId: card.deliveryId, event: .skipped
            )
        }
        AnalyticsManager.shared.track(.affirmationDisplayEnded, properties: [
            "quote_id": card.quote.id,
            "origin": card.origin.rawValue,
            "delivery_id": card.deliveryId ?? "none",
            "dwell_sec": Int(dwell.rounded()),
            "end_cause": cause.rawValue,
            "source": "home",
        ])
        displayedIndex = nil
        displayedAt = nil
    }

    private func recordViewedQuoteIfNeeded(at index: Int) {
        guard deckModel.cards.indices.contains(index) else { return }
        let card = deckModel.cards[index]
        guard lastTrackedQuoteID != card.quote.id else { return }
        lastTrackedQuoteID = card.quote.id
        AnalyticsManager.shared.track(.affirmationViewed, properties: [
            "quote_id": card.quote.id,
            "category": card.quote.categoryID,
            "origin": card.origin.rawValue,
            "delivery_id": card.deliveryId ?? "none",
            "source": "home",
        ])
        let key = "anicca.feed.recent-quote-ids"
        var recent = UserDefaults.standard.stringArray(forKey: key) ?? []
        recent.removeAll { $0 == card.quote.id }
        recent.append(card.quote.id)
        UserDefaults.standard.set(Array(recent.suffix(20)), forKey: key)
    }

    private func feedAction(_ key: String, icon: String, id: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Label(String(localized: String.LocalizationValue(key)), systemImage: icon)
                .font(.caption)
                .foregroundStyle(AppTheme.Colors.label)
                .fixedSize(horizontal: false, vertical: true)
                .frame(minHeight: 44)
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
                        .fill(AppTheme.Colors.accent)
                )
                .overlay(
                    Circle()
                        .stroke(.white.opacity(0.25), lineWidth: 0.5)
                )
                .contentShape(Circle())

        }
        .accessibilityIdentifier(identifier)
    }
}

/// One pager page. Observes the deck model so the card receives the
/// delivery id its display recorded as soon as it exists.
private struct HomeDeckPage: View {
    @ObservedObject var model: HomeDeckModel
    let index: Int
    let pageWidth: CGFloat

    var body: some View {
        if model.cards.indices.contains(index) {
            QuoteCardView(
                quote: model.cards[index].quote,
                pageWidth: pageWidth,
                deliveryId: model.cards[index].deliveryId
            )
        }
    }
}
