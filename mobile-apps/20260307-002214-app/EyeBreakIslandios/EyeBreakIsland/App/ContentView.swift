import SwiftUI

struct ContentView: View {
    @AppStorage(Constants.hasCompletedOnboardingKey) private var hasCompletedOnboarding = false

    var body: some View {
        if hasCompletedOnboarding {
            TimerView()
        } else {
            OnboardingView()
        }
    }
}
