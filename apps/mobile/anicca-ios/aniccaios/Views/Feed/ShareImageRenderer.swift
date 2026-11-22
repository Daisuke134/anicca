import SwiftUI
import Combine
import UIKit

/// Renders a 1080×1920 PNG of a quote on its current theme background, with `aniccaai.com` watermark.
/// The watermark appears ONLY on outbound share assets — never inside the app feed itself.
enum ShareImageRenderer {
    @MainActor
    static func render(content: WordShareContent, background: ThemeID) -> UIImage? {
        let renderer = ImageRenderer(content: BrandedWordShareCard(content: content, background: background)
            .frame(width: 1080, height: 1920).clipped())
        renderer.scale = 1
        return renderer.uiImage
    }

    @MainActor
    static func render(quote: Quote, background: ThemeID, size: CGSize = CGSize(width: 1080, height: 1920)) -> UIImage {
        let view = ShareCardView(quote: quote, background: background)
            .frame(width: size.width, height: size.height)
            .clipped()
        let renderer = ImageRenderer(content: view)
        renderer.scale = 1
        return renderer.uiImage ?? UIImage()
    }
}

private struct ShareCardView: View {
    let quote: Quote
    let background: ThemeID

    var body: some View {
        ZStack {
            background.image
                .resizable()
                .scaledToFill()

            VStack {
                Spacer()
                Text(quote.text)
                    .font(.system(size: 64, weight: .regular, design: .serif))
                    .foregroundStyle(background.foregroundColor)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(.horizontal, 80)
                Spacer()
                Text(verbatim: "aniccaai.com")
                    .font(.system(size: 24, weight: .regular))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 20)
                    .padding(.vertical, 10)
                    .background(AppTheme.Colors.accent, in: Capsule())
                    .padding(.bottom, 80)
            }
        }
    }
}

/// Fixed export typography is independent of the phone's Dynamic Type setting.
private struct BrandedWordShareCard: View {
    let content: WordShareContent
    let background: ThemeID

    var body: some View {
        ZStack {
            background.image.resizable().scaledToFill()
            // A consistent contrast surface keeps every theme readable outside the app.
            Color.black.opacity(0.58)
            VStack(spacing: 40) {
                Text(verbatim: content.brand).font(.system(size: 44, weight: .semibold))
                Text(verbatim: content.dateLabel).font(.system(size: 30))
                Text(verbatim: content.exportText)
                    .font(.system(size: 64, weight: .regular, design: .serif))
                    .minimumScaleFactor(0.1)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .layoutPriority(1)
                Text(verbatim: content.promise)
                    .font(.system(size: 36, weight: .medium))
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
                Text(verbatim: "aniccaai.com").font(.system(size: 28))
            }
            .foregroundStyle(.white)
            .padding(80)
        }
        .environment(\.layoutDirection, .leftToRight)
    }
}
