import SwiftUI

/// Shared motion tokens for the whole product.
///
/// Every value here is copied from an adopted skill's recipe — never tuned
/// by feel, and never taken from a spoken number. Sources:
/// emilkowalski/skills@apple-design (306K installs; distilled from Apple's
/// WWDC design talks) and its companion audit catalog
/// emilkowalski/skills@improve-animations (279K installs, AUDIT.md), plus
/// dpearson2699/swift-ios-skills@swiftui-animation (5.8K installs).
/// Full audit: anicca-ops `files/ui-animation-polish-audit-2026-11-17.md`.
enum AppMotion {
    /// On-screen movement / morphing: ease-in-out, inside the 300ms UI
    /// budget (improve-animations AUDIT §2).
    static let move = Animation.easeInOut(duration: 0.3)

    /// Selection state morph on small elements: ease-in-out at the top of
    /// the 125–200ms small-element band (improve-animations AUDIT §2).
    static let selection = Animation.easeInOut(duration: 0.2)

    /// Progress / reposition: Apple's shipped spring for move and
    /// reposition — damping 1.0 (critically damped, no overshoot),
    /// response 0.4 (apple-design §4 table and Quick Reference).
    static let progress = Animation.spring(response: 0.4, dampingFraction: 1.0)

    /// Button press feedback: scale to 0.97 with a 160ms ease-out
    /// (improve-animations AUDIT §3; apple-design §1).
    static let press = Animation.easeOut(duration: 0.16)
    static let pressScale: CGFloat = 0.97
}

/// Press feedback for tappable controls: the label scales to 0.97 while
/// pressed, so feedback lands on touch-down instead of touch-up
/// (apple-design §1, "Respond on pointer-down"; improve-animations
/// AUDIT §3).
struct PressScaleButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? AppMotion.pressScale : 1)
            .animation(AppMotion.press, value: configuration.isPressed)
    }
}
