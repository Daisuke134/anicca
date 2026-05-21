import SwiftUI

enum AppAnimations {
    static let timerTick = Animation.linear(duration: 1.0)
    static let overlayAppear = Animation.spring(duration: 0.3)
    static let overlayDismiss = Animation.easeOut(duration: 0.3)
    static let cardSelect = Animation.spring(duration: 0.2)
    static let pageTransition = Animation.spring(duration: 0.4)
    static let buttonPress = Animation.easeInOut(duration: 0.1)
    static let successBounce = Animation.spring(duration: 0.5, bounce: 0.3)
}
