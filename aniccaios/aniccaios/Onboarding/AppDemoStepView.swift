import SwiftUI

struct AppDemoStepView: View {
    let next: () -> Void
    @EnvironmentObject var appState: AppState
    @State private var showCard = false

    private var primaryStruggle: ProblemType {
        let struggles = appState.userProfile.struggles
        guard let first = struggles.first,
              let problem = ProblemType(rawValue: first) else {
            return .anxiety
        }
        return problem
    }

    var body: some View {
        VStack(spacing: 24) {
            Text("onboarding_demo_title")
                .font(.title2.weight(.bold))
                .multilineTextAlignment(.center)

            if showCard {
                let content = NudgeContent.contentForToday(for: primaryStruggle)
                NudgeCardContent(
                    icon: primaryStruggle.icon,
                    title: primaryStruggle.notificationTitle,
                    hookText: content.notificationText,
                    detailText: content.detailText,
                    isAIGenerated: false
                )
                .transition(.move(edge: .bottom).combined(with: .opacity))

                Text("onboarding_demo_footer")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }

            Spacer()

            Button(action: next) {
                Text("onboarding_demo_cta")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity)
                    .frame(height: 56)
                    .background(AppTheme.Colors.accent)
                    .clipShape(RoundedRectangle(cornerRadius: 28))
            }
            .padding(.horizontal, 24)
        }
        .padding()
        .onAppear {
            showCard = true
        }
    }
}
