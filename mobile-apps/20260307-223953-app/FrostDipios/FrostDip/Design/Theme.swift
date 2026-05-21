import SwiftUI

enum Theme {
    // MARK: - Colors (DESIGN_SYSTEM tokens)
    enum Colors {
        static let primary = Color(red: 0.08, green: 0.20, blue: 0.35)       // Deep Navy
        static let accent = Color(red: 0.00, green: 0.75, blue: 0.85)        // Electric Cyan
        static let cold = Color(red: 0.53, green: 0.81, blue: 0.92)          // Ice Blue
        static let hot = Color(red: 0.91, green: 0.30, blue: 0.24)           // Warm Red
        static let success = Color(red: 0.20, green: 0.78, blue: 0.35)       // Fresh Green
        static let warning = Color(red: 1.00, green: 0.76, blue: 0.03)       // Amber
        static let destructive = Color(red: 0.86, green: 0.21, blue: 0.27)   // Alert Red
        static let background = Color(uiColor: .systemBackground)
        static let secondaryBackground = Color(uiColor: .secondarySystemBackground)
        static let label = Color(uiColor: .label)
        static let secondaryLabel = Color(uiColor: .secondaryLabel)
    }

    // MARK: - Typography
    enum Typography {
        static let largeTitle = Font.largeTitle.bold()
        static let title = Font.title.bold()
        static let title2 = Font.title2.bold()
        static let title3 = Font.title3.bold()
        static let headline = Font.headline
        static let body = Font.body
        static let callout = Font.callout
        static let subheadline = Font.subheadline
        static let footnote = Font.footnote
        static let caption = Font.caption
        static let timerDisplay = Font.system(size: 72, weight: .bold, design: .monospaced)
        static let hrDisplay = Font.system(size: 36, weight: .semibold, design: .monospaced)
        static let temperatureDisplay = Font.system(size: 24, weight: .medium, design: .monospaced)
        static let timerSmall = Font.system(size: 32, weight: .light, design: .monospaced)
    }

    // MARK: - Spacing (8pt grid)
    enum Spacing {
        static let xxs: CGFloat = 4
        static let xs: CGFloat = 8
        static let sm: CGFloat = 12
        static let md: CGFloat = 16
        static let lg: CGFloat = 24
        static let xl: CGFloat = 32
        static let xxl: CGFloat = 48
        static let xxxl: CGFloat = 64
    }

    // MARK: - Corner Radius
    enum CornerRadius {
        static let small: CGFloat = 8
        static let medium: CGFloat = 12
        static let large: CGFloat = 16
        static let xl: CGFloat = 24
    }

    // MARK: - Animation
    enum Animation {
        static let standard = SwiftUI.Animation.easeInOut(duration: 0.3)
        static let slow = SwiftUI.Animation.easeInOut(duration: 0.6)
        static let spring = SwiftUI.Animation.spring(response: 0.4, dampingFraction: 0.8)
    }
}
