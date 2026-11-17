import SwiftUI
import StoreKit
import Combine

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

    /// Why this word is on screen, shown on the card itself so the
    /// personalization is felt, not just logged (user rule, 2026-11-15:
    /// the simulation's effect must be visible in the experience). Every
    /// deck card comes out of the same ranked, profile-based selection —
    /// the first card is the intervention chosen for this person, the
    /// rest are further words from that same ranking.
    var selectionCaptionKey: String {
        switch origin {
        case .selectedIntervention, .notification: return "feed_chosen_from_answers"
        case .exploration: return "feed_picked_from_answers"
        }
    }
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

/// Idle auto-advance for the living home. The user rejected the old 3s recording
/// dwell on 2026-11-17 because it felt like flashcards, and judged the 20s
/// dwell still too fast the same day. The 29s value is derived, not picked:
/// dwell = design words x seconds per word x repetitions + one breath.
/// - Design words = 15: the p90 of the shipped English pool, measured
///   2026-11-17 (SupplementalAffirmations p90 = 11 words,
///   AdaptiveAffirmationCatalog p90 = 15 words).
/// - Pace = 150 wpm (0.4 s/word): an affirmation is read as subvocal
///   self-talk, near oral-reading speed and inside the conservative
///   on-screen-text band (BBC Subtitle Guidelines 160-180 wpm;
///   DCMP Captioning Key 130-160 wpm).
/// - Repetitions = 3: the niche winner's form (affirmsoftly,
///   "Repeat 3 times" — pattern A13 in the distribution ledger).
/// - Settle = one resonance-frequency breath: 5.5 breaths/min = 10.9 s
///   (Lehrer & Gevirtz, HRV biofeedback).
/// 15 x 0.4 x 3 + 10.9 = 28.9 -> 29 s. Production and recording use the
/// same interval so the recorded experience is the real one. The interval
/// remains an eval-tunable constant, not a design constant.
enum HomeAutoAdvance {
    static let interval: TimeInterval = 29
    static let recordingInterval: TimeInterval = 29

    static var isRecordingMode: Bool {
        ProcessInfo.processInfo.arguments.contains("-aniccaRecordingMode")
    }

    /// Auto-advance is disabled for UI tests unless recording is requested. Maestro
    /// steps can take longer than the idle interval, which moved the deck
    /// mid-assertion in build-830 E2E run 43678244497 (by the time the
    /// flow copied the home quote, the deck had advanced past the
    /// onboarding intervention it is compared against). `-uiTesting` is
    /// the codebase's existing Maestro launch-argument convention
    /// (AppState.resolveDeviceId). Deliberately not the `UITESTING`
    /// argument: SubscriptionManager skips RevenueCat setup under that
    /// one, and the paywall needs real products.
    static var isDisabledForUITesting: Bool {
        ProcessInfo.processInfo.arguments.contains("-uiTesting")
    }

    static func shouldAdvance(
        now: Date,
        lastInteractionAt: Date,
        isSceneActive: Bool,
        cardCount: Int,
        anySheetPresented: Bool,
        interval: TimeInterval = HomeAutoAdvance.interval,
        isUITesting: Bool = HomeAutoAdvance.isDisabledForUITesting,
        isRecordingMode: Bool = HomeAutoAdvance.isRecordingMode
    ) -> Bool {
        guard (!isUITesting || isRecordingMode), isSceneActive, cardCount > 1, !anySheetPresented else { return false }
        return now.timeIntervalSince(lastInteractionAt) >= (isRecordingMode ? recordingInterval : interval)
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
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
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

    private var displayedWordID: String? {
        guard deckModel.cards.indices.contains(currentIndex) else { return nil }
        return deckModel.cards[currentIndex].id
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
                        VerticalPager(count: deckModel.cards.count, currentIndex: $currentIndex, navigationRevision: navigationRevision, reduceMotion: reduceMotion) { index in
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
                // Keep the theme visible beneath the transparent Rive artwork.
                themeStore.image.resizable().scaledToFill()
                    .frame(width: geo.size.width, height: geo.size.height + geo.safeAreaInsets.top + geo.safeAreaInsets.bottom)
                    .scaleEffect(backgroundDrift ? 1.09 : 1.02)
                    .offset(x: backgroundDrift ? -12 : 12)
                    .animation(reduceMotion ? nil : .easeInOut(duration: 26).repeatForever(autoreverses: true), value: backgroundDrift)
                    .clipped()
                    .overlay {
                        LivingRiveBackground(wordID: displayedWordID)
                    }
                    .ignoresSafeArea()
                    .accessibilityHidden(true)
            }
        }
        .environmentObject(themeStore)
        .environmentObject(likedStore)
        .analyticsScreen(.feed, flowID: "feed")
        .onAppear {
            // Ambient drift is motion, so under Reduce Motion the theme
            // stays still (apple-design §14; swiftui-animation checklist).
            if !reduceMotion { backgroundDrift = true }
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
            // No withAnimation wrapper here: VerticalPager owns the word
            // transition. A second, mismatched animation around the binding
            // animates nothing the pager shows (swiftui-animation: scope an
            // animation to what it actually drives).
            currentIndex = HomeAutoAdvance.nextIndex(current: currentIndex, count: deckModel.cards.count)
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
        currentIndex = 0 // VerticalPager owns the transition (see auto-advance).
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
        }
        .buttonStyle(PressScaleButtonStyle())
        .accessibilityIdentifier(id)
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
        .buttonStyle(PressScaleButtonStyle())
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
        .buttonStyle(PressScaleButtonStyle())
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
                deliveryId: model.cards[index].deliveryId,
                selectionCaption: NSLocalizedString(model.cards[index].selectionCaptionKey, comment: "Why this word was chosen for this person")
            )
        }
    }
}
