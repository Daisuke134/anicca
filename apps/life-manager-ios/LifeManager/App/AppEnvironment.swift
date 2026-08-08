import Foundation

struct AppEnvironment: Equatable {
    let isUITesting: Bool

    init(processInfo: ProcessInfo = .processInfo) {
        isUITesting = processInfo.arguments.contains("-uiTesting")
            || processInfo.environment["LIFEMANAGER_TESTING"] == "1"
    }
}
