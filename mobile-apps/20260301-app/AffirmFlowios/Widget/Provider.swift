import WidgetKit

struct Provider: TimelineProvider {
    func placeholder(in context: Context) -> AffirmationEntry {
        AffirmationEntry(
            date: Date(),
            affirmation: "You have the power to create positive change",
            focusArea: .calm
        )
    }

    func getSnapshot(in context: Context, completion: @escaping (AffirmationEntry) -> Void) {
        let entry = getCurrentEntry()
        completion(entry)
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<AffirmationEntry>) -> Void) {
        let entry = getCurrentEntry()

        // Refresh at midnight
        let midnight = Calendar.current.startOfDay(for: Date().addingTimeInterval(86400))
        let timeline = Timeline(entries: [entry], policy: .after(midnight))
        completion(timeline)
    }

    private func getCurrentEntry() -> AffirmationEntry {
        let defaults = UserDefaults.standard
        let content = defaults.string(forKey: "currentAffirmation") ?? "Tap to get your first affirmation"
        let areaRaw = defaults.string(forKey: "currentFocusArea") ?? "Calm"
        let area = FocusArea(rawValue: areaRaw) ?? .calm

        return AffirmationEntry(date: Date(), affirmation: content, focusArea: area)
    }
}
