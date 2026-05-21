import AppIntents
import WidgetKit

struct RefreshAffirmationIntent: AppIntent {
    static var title: LocalizedStringResource = "Refresh Affirmation"
    static var description = IntentDescription("Get a new affirmation")

    func perform() async throws -> some IntentResult {
        // Trigger app to generate new affirmation
        NotificationCenter.default.post(
            name: Notification.Name("RefreshAffirmation"),
            object: nil
        )
        return .result()
    }
}
