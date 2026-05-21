import WidgetKit
import SwiftUI

// MARK: - Timeline Entry
struct DailyDhammaEntry: TimelineEntry {
    let date: Date
    let verseText: String
    let verseSource: String
}

// MARK: - Timeline Provider
struct DailyDhammaProvider: TimelineProvider {
    // Verse data matching verses.ts (free verses only, id 1-8)
    let defaultVerses = [
        ("Hatred never ceases by hatred; by love alone is it healed.", "Dhammapada, Verse 5"),
        ("All things are impermanent. Work out your salvation with diligence.", "Dhammapada, Verse 277"),
        ("Wisdom springs from meditation; without meditation wisdom wanes.", "Dhammapada, Verse 282"),
        ("The mind is everything. What you think, you become.", "Dhammapada, Verse 1-2"),
        ("Better than a thousand hollow words is one word that brings peace.", "Dhammapada, Verse 100"),
        ("Let go of the past, let go of the future. Live fully in the present.", "Dhammapada, Verse 348"),
        ("Peace comes from within. Do not seek it without.", "Dhammapada"),
        ("Wander alone like a rhinoceros horn.", "Khaggavisana Sutta")
    ]

    func placeholder(in context: Context) -> DailyDhammaEntry {
        DailyDhammaEntry(
            date: Date(),
            verseText: "Peace comes from within.",
            verseSource: "Dhammapada"
        )
    }

    func getSnapshot(in context: Context, completion: @escaping (DailyDhammaEntry) -> ()) {
        completion(getDailyEntry())
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<DailyDhammaEntry>) -> ()) {
        let entry = getDailyEntry()

        // Update at midnight local time
        let calendar = Calendar.current
        let tomorrow = calendar.startOfDay(for: calendar.date(byAdding: .day, value: 1, to: Date())!)

        let timeline = Timeline(entries: [entry], policy: .after(tomorrow))
        completion(timeline)
    }

    private func getDailyEntry() -> DailyDhammaEntry {
        let calendar = Calendar.current
        let dayOfYear = calendar.ordinality(of: .day, in: .year, for: Date()) ?? 1
        let index = (dayOfYear - 1) % defaultVerses.count
        let verse = defaultVerses[index]

        return DailyDhammaEntry(date: Date(), verseText: verse.0, verseSource: verse.1)
    }
}

// MARK: - Widget Views
struct DailyDhammaWidgetView: View {
    let entry: DailyDhammaEntry
    @Environment(\.widgetFamily) var family

    var body: some View {
        switch family {
        case .accessoryRectangular:
            AccessoryRectangularView(entry: entry)
        case .accessoryCircular:
            AccessoryCircularView()
        case .accessoryInline:
            AccessoryInlineView(entry: entry)
        case .systemSmall:
            SmallWidgetView(entry: entry)
        case .systemMedium:
            MediumWidgetView(entry: entry)
        default:
            SmallWidgetView(entry: entry)
        }
    }
}

// MARK: - Lock Screen Rectangular
struct AccessoryRectangularView: View {
    let entry: DailyDhammaEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack {
                Image(systemName: "leaf.fill")
                    .font(.caption2)
                Text("Daily Dhamma")
                    .font(.caption2)
                    .fontWeight(.semibold)
            }
            Text(truncateText(entry.verseText, maxLength: 60))
                .font(.caption)
                .lineLimit(2)
        }
        .containerBackground(for: .widget) {
            AccessoryWidgetBackground()
        }
    }
}

// MARK: - Lock Screen Circular
struct AccessoryCircularView: View {
    var body: some View {
        ZStack {
            AccessoryWidgetBackground()
            Image(systemName: "leaf.fill")
                .font(.title2)
        }
        .containerBackground(for: .widget) { }
    }
}

// MARK: - Lock Screen Inline
struct AccessoryInlineView: View {
    let entry: DailyDhammaEntry

    var body: some View {
        ViewThatFits {
            Text("\u{1FAB7} \(truncateText(entry.verseText, maxLength: 30))")
            Text("\u{1FAB7} Daily Dhamma")
        }
    }
}

// MARK: - Home Screen Small
struct SmallWidgetView: View {
    let entry: DailyDhammaEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "leaf.fill")
                    .foregroundColor(Color("AccentColor"))
                Text("Daily Dhamma")
                    .font(.caption)
                    .fontWeight(.semibold)
            }

            Text(truncateText(entry.verseText, maxLength: 80))
                .font(.caption)
                .lineLimit(4)

            Spacer()

            Text(entry.verseSource)
                .font(.caption2)
                .foregroundColor(.secondary)
        }
        .padding()
        .containerBackground(for: .widget) {
            Color("WidgetBackground")
        }
    }
}

// MARK: - Home Screen Medium
struct MediumWidgetView: View {
    let entry: DailyDhammaEntry

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: "leaf.fill")
                        .foregroundColor(Color("AccentColor"))
                    Text("Daily Dhamma")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                }

                Text(entry.verseText)
                    .font(.callout)
                    .lineLimit(3)

                Spacer()

                Text(entry.verseSource)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            Spacer()
        }
        .padding()
        .containerBackground(for: .widget) {
            Color("WidgetBackground")
        }
    }
}

// MARK: - Helper
func truncateText(_ text: String, maxLength: Int) -> String {
    if text.count <= maxLength {
        return text
    }
    let truncated = String(text.prefix(maxLength - 3))
    return truncated + "..."
}

// MARK: - Widget Configuration
@main
struct DailyDhammaWidget: Widget {
    let kind: String = "com.dailydhamma.app.widget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: DailyDhammaProvider()) { entry in
            DailyDhammaWidgetView(entry: entry)
        }
        .configurationDisplayName("Daily Dhamma")
        .description("Today's Buddhist wisdom from the Dhammapada")
        .supportedFamilies([
            .systemSmall,
            .systemMedium,
            .accessoryCircular,
            .accessoryRectangular,
            .accessoryInline
        ])
    }
}

// MARK: - Preview (for Xcode development)
#Preview(as: .accessoryRectangular) {
    DailyDhammaWidget()
} timeline: {
    DailyDhammaEntry(date: .now, verseText: "Peace comes from within.", verseSource: "Dhammapada")
}
