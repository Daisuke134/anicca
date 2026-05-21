import SwiftUI

struct OnboardingView: View {
    @State private var currentPage = 0

    var body: some View {
        TabView(selection: $currentPage) {
            WelcomeView(onContinue: { currentPage = 1 })
                .tag(0)

            FocusAreaSelectionView(onContinue: { currentPage = 2 })
                .tag(1)

            WidgetTutorialView()
                .tag(2)
        }
        .tabViewStyle(.page(indexDisplayMode: .never))
        .ignoresSafeArea()
    }
}

#Preview {
    OnboardingView()
        .environment(UserSettings())
}
