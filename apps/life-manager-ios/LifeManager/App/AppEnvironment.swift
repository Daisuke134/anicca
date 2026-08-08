import Foundation

struct AppEnvironment: Equatable {
    let isUITesting: Bool
    let apiBaseURL: URL?
    let callbackScheme: String

    init(processInfo: ProcessInfo = .processInfo, bundle: Bundle = .main) {
        isUITesting = processInfo.arguments.contains("-uiTesting")
            || processInfo.environment["LIFEMANAGER_TESTING"] == "1"
        apiBaseURL = URL(string: bundle.object(forInfoDictionaryKey: "LIFEMANAGER_API_BASE_URL") as? String ?? "")
        callbackScheme = bundle.object(forInfoDictionaryKey: "LIFEMANAGER_CALLBACK_SCHEME") as? String ?? "lifemanager"
    }

    @MainActor
    func makeViewModel() -> AppViewModel? {
        guard !isUITesting, let apiBaseURL else { return nil }
        return AppComposition(baseURL: apiBaseURL, callbackScheme: callbackScheme).viewModel
    }
}
