import SwiftUI

enum AppTypography {
    static let display = Font.system(size: 56, weight: .bold, design: .rounded)
    static let headline1 = Font.title.bold()
    static let headline2 = Font.title2.weight(.semibold)
    static let headline3 = Font.headline
    static let body = Font.body
    static let callout = Font.callout
    static let subheadline = Font.subheadline
    static let caption1 = Font.caption
    static let caption2 = Font.caption2
    static let timerMono = Font.system(size: 48, weight: .medium, design: .monospaced)
}
