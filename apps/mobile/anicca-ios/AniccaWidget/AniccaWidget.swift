import AppIntents
import WidgetKit
import SwiftUI

struct NudgeEntry: TimelineEntry {
    let date: Date
    let word: WidgetWord?
    let name: String
    let theme: NudgeTheme
    let saved: Bool

    static var safeText: String {
        let language = Locale.preferredLanguages.first ?? "en"
        if language.hasPrefix("ja") { return "自分に優しくしよう。" }
        if language.hasPrefix("es") { return "Sé amable contigo mismo." }
        return "Be kind to yourself."
    }
    var text: String { word?.text ?? Self.safeText }
}

@available(iOS 17.0, *)
struct NudgeTimelineProvider: AppIntentTimelineProvider {
    func placeholder(in context: Context) -> NudgeEntry {
        NudgeEntry(date: Date(), word: nil, name: "Anicca", theme: .sage, saved: false)
    }

    func snapshot(for configuration: NudgeConfiguration, in context: Context) async -> NudgeEntry {
        makeEntry(configuration, date: Date(), lockScreen: context.family == .accessoryRectangular)
    }

    func timeline(for configuration: NudgeConfiguration, in context: Context) async -> Timeline<NudgeEntry> {
        let now = Date()
        let store = WidgetContentStore(defaults: AppGroup.userDefaults)
        let entry = makeEntry(configuration, date: now, lockScreen: context.family == .accessoryRectangular)
        if !context.isPreview, let word = entry.word {
            store.recordPresentation(word, at: now)
        }
        let interval = store.hasPremium(at: now) ? configuration.refresh.interval : NudgeRefresh.daily.interval
        return Timeline(entries: [entry], policy: .after(now.addingTimeInterval(interval)))
    }

    private func makeEntry(_ configuration: NudgeConfiguration, date: Date, lockScreen: Bool) -> NudgeEntry {
        let store = WidgetContentStore(defaults: AppGroup.userDefaults)
        let category = configuration.category == "For you" ? nil : configuration.category
        // Lock screen never receives the personal text, category, or custom name.
        let word = lockScreen ? nil : store.select(category: category, now: date)
        return NudgeEntry(date: date, word: word, name: lockScreen ? "Anicca" : configuration.name,
                          theme: store.hasPremium(at: date) ? configuration.theme : .sage,
                          saved: word.map { store.isSaved($0.id) } ?? false)
    }
}

@available(iOS 17.0, *)
struct AniccaWidget: Widget {
    let kind = "AniccaWidget"

    var body: some WidgetConfiguration {
        AppIntentConfiguration(kind: kind, intent: NudgeConfiguration.self, provider: NudgeTimelineProvider()) { entry in
            NudgeWidgetEntryView(entry: entry)
                .containerBackground(for: .widget) {
                    if entry.theme == .dusk {
                        Color(red: 0.16, green: 0.20, blue: 0.24)
                    } else {
                        WidgetAppearance.gradient
                    }
                }
        }
        .configurationDisplayName("Anicca")
        .description("Words for you. Open Anicca once to sync your words. Lock screen words stay private.")
        .supportedFamilies([.systemSmall, .systemMedium, .systemLarge, .accessoryRectangular])
    }
}

struct NudgeWidgetEntryView: View {
    @Environment(\.widgetFamily) private var family
    let entry: NudgeEntry

    private var openURL: URL {
        var components = URLComponents()
        components.scheme = "anicca"
        components.host = "widget"
        components.queryItems = [URLQueryItem(name: "family", value: String(describing: family))]
        return components.url!
    }

    var body: some View {
        Group {
            if family == .accessoryRectangular {
                Text(NudgeEntry.safeText)
                    .font(.system(size: 12, design: .serif))
                    .minimumScaleFactor(0.8)
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    Text("🪷")
                        .font(family == .systemLarge ? .largeTitle : .title2)
                    Spacer(minLength: 0)
                    Text(entry.text)
                        .font(.system(size: family == .systemLarge ? 24 : 15, design: .serif))
                        .minimumScaleFactor(0.75)
                    Spacer(minLength: 0)
                    Text(entry.name)
                        .font(.caption)
                        .lineLimit(1)
                    if #available(iOS 17.0, *),
                       (family == .systemMedium || family == .systemLarge), let word = entry.word {
                        Button(intent: SaveWidgetWordIntent(wordID: word.id)) {
                            Label(entry.saved ? "Saved" : "Save", systemImage: entry.saved ? "heart.fill" : "heart")
                        }
                        .buttonStyle(.plain)
                        .disabled(entry.saved)
                        .invalidatableContent()
                    }
                }
                .foregroundStyle(entry.theme == .dusk ? .white : WidgetAppearance.label)
            }
        }
        .widgetURL(openURL)
    }
}

// Keep the same kind so installed iOS 16 widgets survive an OS upgrade.
struct LegacyAniccaWidget: Widget {
    let kind = "AniccaWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: LegacyNudgeTimelineProvider()) { entry in
            LegacyNudgeWidgetView(entry: entry)
        }
        .configurationDisplayName("Anicca")
        .description("Words for you. Open Anicca once to sync your words. Lock screen words stay private.")
        .supportedFamilies([.systemSmall, .systemMedium, .systemLarge, .accessoryRectangular])
    }
}

struct LegacyNudgeWidgetView: View {
    @Environment(\.widgetFamily) private var family
    let entry: NudgeEntry

    var body: some View {
        if family == .accessoryRectangular {
            NudgeWidgetEntryView(entry: entry)
        } else {
            NudgeWidgetEntryView(entry: entry)
                .padding()
                .background(WidgetAppearance.gradient)
        }
    }
}

struct LegacyNudgeTimelineProvider: TimelineProvider {
    func placeholder(in context: Context) -> NudgeEntry {
        NudgeEntry(date: Date(), word: nil, name: "Anicca", theme: .sage, saved: false)
    }

    func getSnapshot(in context: Context, completion: @escaping (NudgeEntry) -> Void) {
        completion(makeEntry(in: context, at: Date()))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<NudgeEntry>) -> Void) {
        let now = Date()
        let entry = makeEntry(in: context, at: now)
        if !context.isPreview, let word = entry.word {
            WidgetContentStore(defaults: AppGroup.userDefaults).recordPresentation(word, at: now)
        }
        completion(Timeline(entries: [entry], policy: .after(now.addingTimeInterval(86400))))
    }

    private func makeEntry(in context: Context, at date: Date) -> NudgeEntry {
        let store = WidgetContentStore(defaults: AppGroup.userDefaults)
        let word = context.family == .accessoryRectangular ? nil : store.select(category: nil, now: date)
        return NudgeEntry(date: date, word: word, name: "Anicca", theme: .sage,
                          saved: word.map { store.isSaved($0.id) } ?? false)
    }
}
