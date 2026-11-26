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
        /// The words a tapped notification delivered.
        case notification
        /// Bundled words shown when the Manager engine cannot deliver a
        /// word (unreachable, error, or a `none` decision). The living home
        /// must never be blank: 1.11.0 shipped an empty home to every user
        /// because an unavailable engine suppressed all words.
        case bundledFallback
    }

    let quote: Quote
    var origin: Origin
    var deliveryId: String?

    var id: String { quote.id }

    /// The card is the sampled intervention or an opened notification.
    var selectionCaptionKey: String {
        switch origin {
        case .selectedIntervention, .notification: return "feed_chosen_from_answers"
        case .bundledFallback: return "feed_default_words"
        }
    }
}

/// The bundled fallback deck. Pure and deterministic so it can be unit
/// tested: given the bundled catalog, the deck starts at today's word
/// (same day-rotation as `QuoteProvider.todayQuote`) and continues through
/// the catalog, so the living home rotates on the normal cadence fully
/// offline. It never returns an empty deck while the catalog is non-empty.
enum HomeFallbackDeck {
    static func quotes(language: LanguagePreference, date: Date, count: Int = 8, calendar: Calendar = .current) -> [Quote] {
        let pool = QuoteProvider.shared.all(preferredLanguage: language).filter { !$0.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        guard !pool.isEmpty else { return [] }
        let dayOfYear = calendar.ordinality(of: .day, in: .year, for: date) ?? 1
        let start = (dayOfYear - 1) % pool.count
        let take = min(count, pool.count)
        return (0..<take).map { pool[(start + $0) % pool.count] }
    }
}

/// The deck behind the living home. Published so a card already on screen
/// picks up the delivery id its display records, without waiting for the
/// pager to rebuild the page.
final class HomeDeckModel: ObservableObject {
    @Published var cards: [HomeDeckCard] = []

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
    @State private var wordRequest: UUID?
    @State private var navigationRevision: Int = 0
    @State private var displayedIndex: Int?
    @State private var displayedAt: Date?
    @State private var lastInteractionAt: Date = Date()
    @State private var pendingEndCause: HomeDisplayEndCause = .userSwipe
    @State private var backgroundDrift = false
    @State private var showQuoteShare = false
    @State private var refreshAfterShare = false
    @State private var showSettings = false
    @State private var showSaved = false
    @State private var showReminders = false
    @State private var showThemes = false
    @State private var lastTrackedQuoteID: String?
    /// Poyo: true when this launch is a return after a long absence
    /// (the face is then always happy — a reunion that does not blame).
    @State private var isReturningAfterAbsence = false

    private let autoAdvanceTimer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    private var managePaymentURL: URL {
        appState.subscriptionInfo.managementURL
            ?? URL(string: "https://apps.apple.com/account/subscriptions")!
    }

    private var anySheetPresented: Bool {
        showSettings || showSaved || showReminders || showThemes || showQuoteShare
    }

    private var displayedWordID: String? {
        guard deckModel.cards.indices.contains(currentIndex) else { return nil }
        return deckModel.cards[currentIndex].id
    }

    /// Poyo's face for the currently visible card (wiring spec §4):
    /// time of day + the no-blame reunion rule. The home deck carries no
    /// intervention type, so the selector's context rules fall through to
    /// the time-of-day rules.
    private var currentPoyoExpression: PoyoExpression {
        let hour = Calendar.current.component(.hour, from: Date())
        return PoyoExpression.select(
            interventionType: nil,
            hour: hour,
            isReturningAfterAbsence: isReturningAfterAbsence
        )
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
                            HomeDeckPage(model: deckModel, index: index, pageWidth: geo.size.width, onSharePresentationChange: sharePresentationChanged)
                                .frame(width: contentGeometry.size.width, height: contentGeometry.size.height)
                                .environmentObject(themeStore)
                                .environmentObject(likedStore)
                        }
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
            .overlay(alignment: .bottomTrailing) {
                // Poyo — resident beside the words, bottom-right, clear of
                // the bottom action bar. Decorative layer: if the asset
                // ever fails to load, the words are unaffected (the home
                // must never be empty because of Poyo).
                if deckModel.cards.indices.contains(currentIndex) {
                    PoyoView(expression: currentPoyoExpression,
                             size: 72,
                             seed: deckModel.cards[currentIndex].id)
                        .padding(.trailing, 20)
                        .padding(.bottom, 96)
                        .allowsHitTesting(false)
                }
            }
        }
        // The identifier names the home screen itself, not the deck pager.
        // Since the Manager switch (PR #9399) the deck could be empty
        // whenever there was no intervention to show — a `none` decision, an
        // unavailable engine, or a signed-out session (sign-in is skippable
        // by design) — and the home must still be the identifiable screen
        // onboarding lands on. Attached to the pager only, `feed-today`
        // never existed in those states and the onboarding ship gate failed
        // at the paywall-close assertion on the #9399 merge run.
        // 1.11.1: the deck is no longer allowed to stay empty — bundled
        // fallback words fill it whenever the engine delivers nothing —
        // but the identifier stays on the screen for the same reason.
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("feed-today")
        .environmentObject(themeStore)
        .environmentObject(likedStore)
        .analyticsScreen(.feed, flowID: "feed")
        .onAppear {
            // Ambient drift is motion, so under Reduce Motion the theme
            // stays still (apple-design §14; swiftui-animation checklist).
            if !reduceMotion { backgroundDrift = true }
            isReturningAfterAbsence = PoyoPresence.isReturningAfterAbsence(now: Date())
            PoyoPresence.markSeen(now: Date())
            PoyoAttachmentStore.exportExpressionsIfNeeded()
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
                wordRequest = nil
                endDisplay(cause: .appClosed)
            default:
                break
            }
        }
        .onChange(of: appState.authStatus.userId) { _ in refreshToday() }
        .onChange(of: appState.syntheticUser.answerSnapshot.values) { _ in refreshToday() }
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
        if deckModel.cards.isEmpty { refreshToday(); return }
        guard currentIndex != 0 else { return }
        pendingEndCause = .userSwipe
        currentIndex = 0 // VerticalPager owns the transition (see auto-advance).
    }

    private func sharePresentationChanged(_ presented: Bool) {
        showQuoteShare = presented
        lastInteractionAt = Date()
        guard !presented else { return }
        if refreshAfterShare {
            refreshAfterShare = false
            refreshToday()
        } else {
            applyPendingQuoteNavigation()
        }
        if displayedIndex == nil, !deckModel.cards.isEmpty { beginDisplay(at: currentIndex) }
    }

    private func refreshToday() {
        guard !showQuoteShare else {
            refreshAfterShare = true
            return
        }
        let now = Date()
        appState.refreshSyntheticUserIfNeeded(now: now)
        let language = appState.effectiveLanguage
        let request = UUID()
        wordRequest = request
        let user = appState.syntheticUser
        endDisplay(cause: .replaced)
        deckModel.cards = []
        applyPendingQuoteNavigation()
        guard wordRequest == request else { return }
        // The home must never be blank. Bundled words go up immediately —
        // before any network answer — and stay up unless the Manager
        // delivers a chosen word to replace them. This works offline, on
        // first launch, and while signed out. (1.11.0 regression: an
        // unavailable engine left the deck empty for every user.)
        if deckModel.cards.isEmpty { buildFallbackDeck(language: language, now: now) }
        Task { @MainActor in
            do {
                let decision = try await ModelWordsService.shared.today(user: user, language: language.rawValue, now: now)
                guard wordRequest == request, appState.syntheticUser.personId == user.personId,
                      appState.effectiveLanguage == language else { return }
                guard !showQuoteShare else {
                    refreshAfterShare = true
                    return
                }
                if let quote = decision.quote {
                    buildDeck(selected: .init(quote: quote, deliveryId: decision.deliveryID), language: language, now: now)
                }
                // A `none` decision (quote == nil) keeps the bundled words:
                // the person still gets words today; only the personalized
                // intervention is withheld.
            } catch {
                // Engine unreachable or error: the bundled fallback deck
                // built above stays on screen.
            }
            if wordRequest == request {
                applyPendingQuoteNavigation()
                if deckModel.cards.isEmpty { buildFallbackDeck(language: language, now: now) }
            }
        }
    }

    private func buildFallbackDeck(language: LanguagePreference, now: Date) {
        let quotes = HomeFallbackDeck.quotes(language: language, date: now)
        guard !quotes.isEmpty else { return }
        endDisplay(cause: .replaced)
        deckModel.cards = quotes.map { HomeDeckCard(quote: $0, origin: .bundledFallback) }
        currentIndex = 0
        navigationRevision += 1
        lastInteractionAt = Date()
        beginDisplay(at: 0)
    }

    private func buildDeck(selected presentation: DailyAffirmationStore.Presentation, language: LanguagePreference, now: Date, firstOrigin: HomeDeckCard.Origin = .selectedIntervention) {
        endDisplay(cause: .replaced)
        var cards = [HomeDeckCard(quote: presentation.quote, origin: firstOrigin, deliveryId: presentation.deliveryId)]
        // Behind the chosen word, the rest of today's deck: bundled words,
        // so the living home keeps changing on its own at the established
        // cadence. A single-card deck freezes on one phrase all day, which
        // the founder rejected (2026-11-23): the home is a garden — never
        // empty, never frozen. The Manager's word stays first and is the
        // recorded intervention; the tail is labelled bundledFallback.
        for quote in HomeFallbackDeck.quotes(language: language, date: now) where quote.id != presentation.quote.id {
            cards.append(HomeDeckCard(quote: quote, origin: .bundledFallback))
        }
        deckModel.cards = cards
        currentIndex = 0
        navigationRevision += 1
        lastInteractionAt = Date()
        beginDisplay(at: 0)
    }

    private func applyPendingQuoteNavigation() {
        guard !showQuoteShare else { return }
        var catalog = QuoteProvider.shared.all(preferredLanguage: appState.effectiveLanguage)
        if let first = deckModel.cards.first, !catalog.contains(where: { $0.id == first.quote.id }) {
            catalog.append(first.quote)
        }
        let notificationDeliveryId = quoteNavigation.pendingRequest?.deliveryId
        guard let destination = quoteNavigation.resolveQuote(in: catalog) else { return }
        wordRequest = nil // A notification tap wins over any in-flight home request.
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
        // Older cached presentations have no assignment ID or propensity.
        // Bundled fallback cards are not Manager deliveries: never mint a
        // delivery id for them, or the bench would count words the engine
        // never assigned.
        if deckModel.cards[index].deliveryId == nil, deckModel.cards[index].origin != .bundledFallback {
            deckModel.cards[index].deliveryId = UUID().uuidString
        }
        let deliveredCard = deckModel.cards[index]
        if let deliveryId = deliveredCard.deliveryId {
            DecisionPointRecorder.shared.recordDelivery(deliveryId: deliveryId, messageId: deliveredCard.quote.id, source: "home")
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
    let onSharePresentationChange: (Bool) -> Void

    var body: some View {
        if model.cards.indices.contains(index) {
            QuoteCardView(
                quote: model.cards[index].quote,
                pageWidth: pageWidth,
                deliveryId: model.cards[index].deliveryId,
                selectionCaption: NSLocalizedString(model.cards[index].selectionCaptionKey, comment: "Why this word was chosen for this person"),
                onSharePresentationChange: onSharePresentationChange
            )
        }
    }
}
