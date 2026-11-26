import Foundation

/// Frozen at the tap, so a new home word or midnight cannot change an open share.
struct WordShareContent: Identifiable {
    let id = UUID().uuidString
    let quote: Quote
    let date: Date
    let dateLabel: String
    let promise: String
    let brand = "アニッチャ / Anicca"
    let dayJST: String

    /// Reflow arbitrary model whitespace in the export; preserve every word and
    /// the untouched original quote for attribution. Hundreds of explicit line
    /// breaks cannot fit a portrait card even when text scales down.
    var exportText: String {
        quote.text.components(separatedBy: .whitespacesAndNewlines)
            .filter { !$0.isEmpty }.joined(separator: " ")
    }

    var caption: String { "\(promise)\nhttps://aniccaai.com\n#アニッチャ #AniccaWords @anicca.company" }

    init(quote: Quote, date: Date = Date()) {
        self.quote = quote
        self.date = date
        dateLabel = date.formatted(date: .abbreviated, time: .omitted)
        promise = String(localized: "quote_share_promise")
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.timeZone = TimeZone(identifier: "Asia/Tokyo")
        formatter.dateFormat = "yyyy-MM-dd"
        dayJST = formatter.string(from: date)
    }

    /// Release enablement is separate from implementation (#520 + E2E + TestFlight).
    static func isEnabled(in bundle: Bundle = .main, arguments: [String] = ProcessInfo.processInfo.arguments) -> Bool {
        #if DEBUG
        if arguments.contains("-aniccaScreenshotSharing") { return true }
        #endif
        return bundle.object(forInfoDictionaryKey: "AniccaScreenshotSharingEnabled") as? Bool ?? false
    }
}
