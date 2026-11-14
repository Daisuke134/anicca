import SwiftUI

struct StrugglesStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState

    /// Legacy bridge kept for the problem-nudge system: the previous
    /// onboarding option ids and the ProblemType values they saved.
    static let problemMapping: [String: String] = [
        "negative_thoughts": "self_loathing",
        "putting_off": "procrastination",
        "anxiety_overwhelm": "anxiety",
        "stuck_habit": "rumination",
        "emotions_take_over": "anger"
    ]

    static func mappedProblems(from struggles: [String]) -> [String] {
        struggles.compactMap { problemMapping[$0] }
    }

    /// Phase 1 pain points, exactly the answer set of the answer→change
    /// mapping (stress / anxiety / self_doubt / procrastination / sleep).
    /// Labels reuse the existing problem_* localization keys.
    private let options: [(id: String, labelKey: String)] = [
        ("stress", "problem_stress"),
        ("anxiety", "problem_anxiety"),
        ("self_doubt", "problem_self_doubt"),
        ("procrastination", "problem_procrastination"),
        ("sleep", "problem_poor_sleep")
    ]

    @State private var selected: Set<String> = []

    var body: some View {
        VStack(spacing: 24) {
            Text(String(localized: "onboarding_struggles_title"))
                .font(.system(size: 36, weight: .bold))
                .fontWeight(.heavy)
                .lineSpacing(4) // line-height 40px
                .minimumScaleFactor(0.8)
                .multilineTextAlignment(.center)
                .foregroundStyle(AppTheme.Colors.label)
                .padding(.top, 40)
                .padding(.horizontal, 24)

            Text(String(localized: "onboarding_struggles_subtitle"))
                .font(.system(size: 16))
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)

            ScrollView {
                VStack(spacing: 12) {
                    ForEach(options, id: \.id) { option in
                        listRow(option: option)
                    }
                }
                .padding(.horizontal, 24)
                .padding(.top, 8)
                .padding(.bottom, 16)
            }

            Button {
                let chosen = options.map(\.id).filter { selected.contains($0) }
                // Phase 1: the answers land in the personalization profile
                // (the mapping's stable ids), and the subset with a true
                // ProblemType counterpart is bridged into the legacy
                // profile so the feed and problem nudges keep working.
                var personalization = appState.personalizationProfile
                personalization.painPointIds = chosen
                appState.updatePersonalizationProfile(personalization)
                var profile = appState.userProfile
                profile.problems = chosen.compactMap(PersonalizationRules.problemTypeBridge)
                appState.updateUserProfile(profile, sync: true)
                next()
            } label: {
                Text(String(localized: "common_next"))
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity)
                    .frame(height: 56)
                    .background(selected.isEmpty ? AppTheme.Colors.label.opacity(0.5) : AppTheme.Colors.label)
                    .clipShape(RoundedRectangle(cornerRadius: 28))
            }
            .disabled(selected.isEmpty)
            .accessibilityIdentifier("onboarding-struggles-next")
            .padding(.horizontal, 24)
            .padding(.bottom, 64)
        }
        .background(AppBackground())
        .onAppear {
            // Forward-only flow: no restoration needed
        }
    }

    @ViewBuilder
    private func listRow(option: (id: String, labelKey: String)) -> some View {
        let isSelected = selected.contains(option.id)
        Button {
            if isSelected {
                selected.remove(option.id)
            } else {
                selected.insert(option.id)
            }
        } label: {
            HStack(spacing: 12) {
                Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 22))
                    .foregroundColor(isSelected ? AppTheme.Colors.accent : .secondary)
                Text(NSLocalizedString(option.labelKey, comment: ""))
                    .font(.system(size: 16, weight: .medium))
                    .foregroundColor(AppTheme.Colors.label)
                Spacer()
            }
            .padding(.horizontal, 16)
            .frame(maxWidth: .infinity, minHeight: 56)
            .background(isSelected ? AppTheme.Colors.accent.opacity(0.15) : AppTheme.Colors.buttonUnselected)
            .clipShape(RoundedRectangle(cornerRadius: 12))
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("onboarding-struggle-\(option.id)")
    }
}



