import AppIntents
import WidgetKit

struct WidgetCategoryOptions: DynamicOptionsProvider {
    func defaultResult() async -> String? { "For you" }

    func results() async throws -> [String] {
        ["For you"] + Set(WidgetContentStore(defaults: AppGroup.userDefaults).words.map(\.category)).sorted()
    }
}

enum NudgeTheme: String, AppEnum {
    case sage, dusk
    static let typeDisplayRepresentation: TypeDisplayRepresentation = "Theme"
    static let caseDisplayRepresentations: [NudgeTheme: DisplayRepresentation] = [
        .sage: "Sage (free)", .dusk: "Dusk (Premium)"
    ]
}

enum NudgeRefresh: String, AppEnum {
    case daily, sixHours, hourly
    static let typeDisplayRepresentation: TypeDisplayRepresentation = "Refresh"
    static let caseDisplayRepresentations: [NudgeRefresh: DisplayRepresentation] = [
        .daily: "Daily (free)", .sixHours: "Every 6 hours (Premium)", .hourly: "Hourly (Premium)"
    ]
    var interval: TimeInterval {
        switch self {
        case .daily: return 86400
        case .sixHours: return 21600
        case .hourly: return 3600
        }
    }
}

@available(iOS 17.0, *)
struct NudgeConfiguration: WidgetConfigurationIntent {
    static let title: LocalizedStringResource = "Your Anicca widget"
    static let description = IntentDescription("Choose your words. Extra themes and refresh frequencies require Premium. iOS controls actual refresh timing.")

    @Parameter(title: "Name", default: "Anicca") var name: String
    @Parameter(title: "Category", optionsProvider: WidgetCategoryOptions()) var category: String
    @Parameter(title: "Theme", default: .sage) var theme: NudgeTheme
    @Parameter(title: "Refresh", default: .daily) var refresh: NudgeRefresh
}

struct SaveWidgetWordIntent: AppIntent {
    static let title: LocalizedStringResource = "Save affirmation"
    static let openAppWhenRun = false
    @Parameter(title: "Word ID") var wordID: String

    init() {}
    init(wordID: String) { self.wordID = wordID }

    func perform() async throws -> some IntentResult {
        let store = WidgetContentStore(defaults: AppGroup.userDefaults)
        if let word = store.words.first(where: { $0.id == wordID }) {
            store.save(word)
            WidgetCenter.shared.reloadTimelines(ofKind: "AniccaWidget")
        }
        return .result()
    }
}
