import SwiftUI
import Combine
import StoreKit
import UIKit

/// Today's affirmation; the home owns its background and scrolls only when text needs more room.
struct QuoteCardView: View {
    let quote: Quote
    let pageWidth: CGFloat
    var deliveryId: String? = nil
    /// Why this word was chosen, when the surface knows (the living home
    /// passes it; other surfaces leave it nil and stay unchanged).
    var selectionCaption: String? = nil
    var onSharePresentationChange: (Bool) -> Void = { _ in }

    @EnvironmentObject var themeStore: ThemeStore
    @EnvironmentObject var likedStore: LikedQuotesStore
    @Environment(\.requestReview) private var requestReview

    private struct ShareSession: Identifiable {
        let content: WordShareContent
        let image: UIImage
        let deliveryId: String?
        let branded: Bool
        var id: String { content.id }
    }
    @State private var shareSession: ShareSession?
    @State private var shareRenderFailed = false
    @State private var copyFlashOpacity: Double = 0
    @ScaledMetric(relativeTo: .title) private var quoteFontSize: CGFloat = 32

    var body: some View {
        VStack(spacing: 32) {
            Spacer()

            if let selectionCaption {
                Text(selectionCaption)
                    .font(.footnote)
                    .foregroundStyle(themeStore.selected.foregroundColor.opacity(0.65))
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(width: max(120, pageWidth - 64))
                    .accessibilityIdentifier("quote-selection-caption")
            }

            Text(quote.text)
                .font(.system(size: quoteFontSize, weight: .regular, design: .serif))
                .foregroundStyle(themeStore.selected.foregroundColor)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
                .frame(width: max(120, pageWidth - 64))
                .accessibilityIdentifier("quote-text")

            if WordShareContent.isEnabled() {
                Button(action: beginShare) {
                    Label(String(localized: "quote_share_action"), systemImage: "square.and.arrow.up")
                        .font(.callout)
                        .foregroundStyle(themeStore.selected.foregroundColor)
                        .padding(.horizontal, 16)
                        .frame(minHeight: 44)
                }
                .buttonStyle(PressScaleButtonStyle())
                .accessibilityIdentifier("quote-share")
            }

            actionRow

            if copyFlashOpacity > 0 {
                Text(String(localized: "quote_copied"))
                    .font(.footnote)
                    .foregroundStyle(.white)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 6)
                    .background(.black.opacity(0.4), in: Capsule())
                    .opacity(copyFlashOpacity)
            }

            Spacer()
            Spacer().frame(height: 32)
        }
        .frame(width: pageWidth)
        .sheet(item: $shareSession, onDismiss: { onSharePresentationChange(false) }) { session in
            ShareSheet(items: [session.image, session.branded ? session.content.caption : "aniccaai.com"], onComplete: {
                DecisionPointRecorder.shared.recordQuoteResponse(messageId: session.content.quote.id, deliveryId: session.deliveryId, event: .shared)
                AnalyticsManager.shared.track(.affirmationShared, properties: ["quote_id": session.content.quote.id, "category": session.content.quote.categoryID])
                if session.branded { trackShare(.screenshotShareCompleted, session: session) }
            }, onPresented: {
                if session.branded { trackShare(.screenshotShareOpened, session: session) }
            })
        }
        .alert(String(localized: "quote_share_failed"), isPresented: $shareRenderFailed) {
            Button(String(localized: "common_close"), role: .cancel) {}
        }
    }

    private func beginShare() {
        guard shareSession == nil else { return }
        let content = WordShareContent(quote: quote)
        let branded = WordShareContent.isEnabled()
        let image = branded
            ? ShareImageRenderer.render(content: content, background: themeStore.selected)
            : ShareImageRenderer.render(quote: quote, background: themeStore.selected)
        guard let image, image.size.width > 0 else {
            shareRenderFailed = true
            return
        }
        onSharePresentationChange(true)
        shareSession = ShareSession(content: content, image: image, deliveryId: deliveryId, branded: branded)
    }

    private func trackShare(_ event: AnalyticsEvent, session: ShareSession) {
        AnalyticsManager.shared.track(event, properties: [
            "share_id": session.id,
            "share_day_jst": session.content.dayJST,
            "quote_id": session.content.quote.id,
            "delivery_id": session.deliveryId ?? "none",
            "source": selectionCaption == nil ? "saved" : "home",
            "asset_version": "word-card-v1"
        ])
    }

    private var actionRow: some View {
        HStack(spacing: 40) {
            if !WordShareContent.isEnabled() {
                actionButton(systemName: "square.and.arrow.up", identifier: "quote-share", action: beginShare)
            }

            actionButton(
                systemName: likedStore.isLiked(quote.id) ? "heart.fill" : "heart",
                identifier: "quote-like"
            ) {
                let didFavorite = likedStore.toggle(quote, themeID: themeStore.selected.rawValue)
                AnalyticsManager.shared.track(didFavorite ? .affirmationLiked : .affirmationUnliked, properties: ["quote_id": quote.id, "category": quote.categoryID, "source": "feed"])
                UIImpactFeedbackGenerator(style: .soft).impactOccurred()
                if didFavorite {
                    DecisionPointRecorder.shared.recordQuoteResponse(messageId: quote.id, deliveryId: deliveryId, event: .saved)
                    ReviewPromptCoordinator.shared.requestReviewIfAppropriate {
                        requestReview()
                    }
                }
            }

            actionButton(systemName: "doc.on.doc", identifier: "quote-copy") {
                UIPasteboard.general.string = quote.text
                UIImpactFeedbackGenerator(style: .light).impactOccurred()
                withAnimation(.easeOut(duration: 0.2)) { copyFlashOpacity = 1 }
                // The exit takes ease-out like every UI exit, and the hold
                // is an animation delay — never a DispatchQueue timer
                // (swiftui-animation, Common Mistakes #5; improve-animations
                // AUDIT §2: ease-in on UI is always a finding, and toasts
                // are the documented 400ms exception).
                withAnimation(.easeOut(duration: 0.4).delay(1.4)) { copyFlashOpacity = 0 }
            }
        }
    }

    private func actionButton(systemName: String, identifier: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: systemName)
                .font(.system(size: 22, weight: .regular))
                .foregroundStyle(themeStore.selected.foregroundColor)
                .frame(width: 44, height: 44)
                .contentShape(Rectangle())
        }
        .buttonStyle(PressScaleButtonStyle())
        .accessibilityIdentifier(identifier)
    }
}

/// UIActivityViewController wrapper.
struct ShareSheet: UIViewControllerRepresentable {
    let items: [Any]
    var onComplete: (() -> Void)? = nil
    var onPresented: (() -> Void)? = nil
    func makeUIViewController(context: Context) -> UIActivityViewController {
        let controller = PresentedShareController(activityItems: items, applicationActivities: nil)
        controller.onPresented = onPresented
        controller.completionWithItemsHandler = { _, completed, _, error in
            if completed && error == nil { Task { @MainActor in onComplete?() } }
        }
        return controller
    }
    func updateUIViewController(_ controller: UIActivityViewController, context: Context) {}
}

/// UIKit calls this only when the sheet actually appears, once per share attempt.
private final class PresentedShareController: UIActivityViewController {
    var onPresented: (() -> Void)?
    private var didRecordPresentation = false

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        guard !didRecordPresentation else { return }
        didRecordPresentation = true
        onPresented?()
    }
}
