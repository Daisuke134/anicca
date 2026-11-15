import Foundation
import WidgetKit

enum NudgeWidgetDataStore {
    static func sync(struggles: [String]) {
        var words: [WidgetWord] = []
        for struggle in Set(struggles).sorted() {
            guard let problem = ProblemType(rawValue: struggle) else { continue }
            for i in 1...60 {
                let key = "nudge_\(problem.rawValue)_notification_\(i)"
                let text = NSLocalizedString(key, comment: "")
                if text != key {
                    words.append(WidgetWord(id: key, text: text, category: struggle))
                }
            }
        }
        let store = WidgetContentStore(defaults: AppGroup.userDefaults)
        if store.words != words {
            store.sync(words)
            WidgetCenter.shared.reloadTimelines(ofKind: "AniccaWidget")
        }
    }
}
