import SwiftUI

struct ContentView: View {
    @Environment(UserSettings.self) private var settings

    var body: some View {
        if settings.onboardingComplete {
            HomeView()
        } else {
            OnboardingView()
        }
    }
}

#Preview {
    ContentView()
        .environment(UserSettings())
}
