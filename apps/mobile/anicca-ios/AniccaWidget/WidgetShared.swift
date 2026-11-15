import Foundation
import SwiftUI

// MARK: - AppGroup (Widget copy — same logic as main app)

enum AppGroup {
    private static let candidateIdentifiers = [
        "group.ai.anicca.app.ios",
        "group.ai.anicca.app"
    ]

    private static let resolvedSuiteName: String = {
        for identifier in candidateIdentifiers {
            if FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: identifier) != nil {
                return identifier
            }
        }
        return candidateIdentifiers[0]
    }()

    private static let cachedDefaults: UserDefaults = {
        guard let defaults = UserDefaults(suiteName: resolvedSuiteName) else {
            fatalError("Unable to create UserDefaults for app group \(resolvedSuiteName)")
        }
        return defaults
    }()

    static var suiteName: String { resolvedSuiteName }
    static var userDefaults: UserDefaults { cachedDefaults }
}

// Widget extension has its own target; keep its palette aligned with AppTheme.
enum WidgetAppearance {
    static let accent = Color(red: 48 / 255, green: 92 / 255, blue: 69 / 255)
    static let label = Color(red: 57 / 255, green: 54 / 255, blue: 52 / 255)
    static let background = Color(red: 241 / 255, green: 241 / 255, blue: 232 / 255)
    static let gradient = LinearGradient(
        colors: [background, Color(red: 227 / 255, green: 233 / 255, blue: 218 / 255)],
        startPoint: .topTrailing, endPoint: .bottomLeading
    )
}
