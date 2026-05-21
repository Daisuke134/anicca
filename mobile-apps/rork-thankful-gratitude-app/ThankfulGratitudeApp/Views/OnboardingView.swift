import SwiftUI

struct OnboardingView: View {
    let language: AppLanguage
    let onComplete: () -> Void

    @State private var currentPage: Int = 0

    private var pages: [(icon: String, title: String, subtitle: String)] {
        [
            ("sun.and.horizon.fill", L10n.onboardingTitle1(language), L10n.onboardingSubtitle1(language)),
            ("sparkles", L10n.onboardingTitle2(language), L10n.onboardingSubtitle2(language)),
            ("flame.fill", L10n.onboardingTitle3(language), L10n.onboardingSubtitle3(language)),
        ]
    }

    var body: some View {
        VStack(spacing: 0) {
            TabView(selection: $currentPage) {
                ForEach(0..<3, id: \.self) { index in
                    onboardingPage(
                        icon: pages[index].icon,
                        title: pages[index].title,
                        subtitle: pages[index].subtitle,
                        index: index
                    )
                    .tag(index)
                }
            }
            .tabViewStyle(.page(indexDisplayMode: .never))
            .animation(.easeInOut, value: currentPage)

            VStack(spacing: 20) {
                HStack(spacing: 8) {
                    ForEach(0..<3, id: \.self) { index in
                        Capsule()
                            .fill(index == currentPage ? Color(red: 0.83, green: 0.65, blue: 0.46) : Color(red: 0.83, green: 0.65, blue: 0.46).opacity(0.3))
                            .frame(width: index == currentPage ? 24 : 8, height: 8)
                            .animation(.spring(duration: 0.3), value: currentPage)
                    }
                }

                Button {
                    if currentPage < 2 {
                        withAnimation { currentPage += 1 }
                    } else {
                        onComplete()
                    }
                } label: {
                    Text(currentPage < 2 ? L10n.continueText(language) : L10n.startFreeTrial(language))
                        .font(.headline)
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 56)
                        .background(
                            LinearGradient(
                                colors: [Color(red: 0.83, green: 0.65, blue: 0.46), Color(red: 0.76, green: 0.55, blue: 0.36)],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .clipShape(.rect(cornerRadius: 16))
                }
                .sensoryFeedback(.impact(weight: .light), trigger: currentPage)

                if currentPage < 2 {
                    Button {
                        onComplete()
                    } label: {
                        Text(L10n.skipText(language))
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 40)
            .frame(maxWidth: 700)
            .frame(maxWidth: .infinity)
        }
        .background(
            LinearGradient(
                colors: [Color(red: 1.0, green: 0.98, blue: 0.95), Color(red: 0.99, green: 0.94, blue: 0.88)],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()
        )
    }

    private func onboardingPage(icon: String, title: String, subtitle: String, index: Int) -> some View {
        VStack(spacing: 24) {
            Spacer()

            ZStack {
                Circle()
                    .fill(
                        RadialGradient(
                            colors: [Color(red: 0.83, green: 0.65, blue: 0.46).opacity(0.2), .clear],
                            center: .center,
                            startRadius: 0,
                            endRadius: 80
                        )
                    )
                    .frame(width: 160, height: 160)

                Image(systemName: icon)
                    .font(.system(size: 64))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [Color(red: 0.83, green: 0.65, blue: 0.46), Color(red: 0.49, green: 0.71, blue: 0.62)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
            }

            VStack(spacing: 12) {
                Text(title)
                    .font(.title.bold())
                    .multilineTextAlignment(.center)

                Text(subtitle)
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 16)
            }

            Spacer()
            Spacer()
        }
        .padding(.horizontal, 24)
    }
}
