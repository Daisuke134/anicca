import SwiftUI
import Combine
import UIKit

/// Anicca app root: full-bleed vertical paging feed.
/// Background = single theme image shared across ALL quotes. Swiping changes the quote text only.
/// Top chrome (hamburger + settings) is locked in place, never moves on swipe.
struct FeedRootView: View {
    @StateObject private var themeStore = ThemeStore()
    @StateObject private var likedStore = LikedQuotesStore()
    @State private var quotes: [Quote] = []
    @State private var currentIndex: Int = 0
    @State private var showSettings = false

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

                // Vertical paging — each page is forced to screen width.
                VerticalPager(count: quotes.count, currentIndex: $currentIndex) { idx in
                    QuoteCardView(quote: quotes[idx], pageWidth: geo.size.width)
                        .frame(width: geo.size.width, height: geo.size.height)
                        .environmentObject(themeStore)
                        .environmentObject(likedStore)
                }
                .frame(width: geo.size.width, height: geo.size.height)
                .accessibilityIdentifier("feed-scroll")

                // Top chrome — single settings button pinned top-right.
                HStack {
                    Spacer()
                    chromeButton(systemName: "slider.horizontal.3", identifier: "feed-settings") {
                        showSettings = true
                    }
                }
                .padding(.horizontal, 16)
                .padding(.top, 8)
                .zIndex(10)
            }
        }
        .environmentObject(themeStore)
        .environmentObject(likedStore)
        .onAppear {
            if quotes.isEmpty {
                quotes = QuoteProvider.shared.all()
            }
        }
        .sheet(isPresented: $showSettings) {
            if #available(iOS 16.0, *) {
                NavigationStack {
                    SettingsSheet()
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
        .onReceive(NotificationCenter.default.publisher(for: .aniccaScrollToQuote)) { note in
            guard let qid = note.userInfo?["quoteId"] as? String else { return }
            if let idx = quotes.firstIndex(where: { $0.id == qid }) {
                withAnimation { currentIndex = idx }
            }
        }
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

extension Notification.Name {
    /// Posted when a notification is tapped or `anicca://quote/<id>` is opened.
    /// userInfo: ["quoteId": "qNNN"]
    static let aniccaScrollToQuote = Notification.Name("AniccaScrollToQuote")
}
