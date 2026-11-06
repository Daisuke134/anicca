import SwiftUI

enum InitialExperienceStyle {
    static let accent = Color(red: 0.19, green: 0.36, blue: 0.27)

    static var background: some View {
        LinearGradient(
            colors: [AppTheme.Colors.background, Color(light: Color(hex: "#e4ecdc"), dark: Color(hex: "#26392d"))],
            startPoint: .topTrailing, endPoint: .bottomLeading
        ).ignoresSafeArea()
    }
}

struct AffirmationGoalStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState
    @State private var selection: String = "self_love"

    private let options = [
        ("self_love", "growth_goal_self_love", "heart"),
        ("calm", "growth_goal_calm", "leaf"),
        ("confidence", "growth_goal_confidence", "sun.max"),
        ("letting_go", "growth_goal_letting_go", "wind")
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("Anicca").font(.system(size: 28, design: .serif)).padding(.top, 20)
            Spacer(minLength: 12)
            Text(String(localized: "growth_goal_title"))
                .font(.system(.largeTitle, design: .serif)).fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)
            Text(String(localized: "growth_goal_subtitle"))
                .font(.subheadline).foregroundStyle(.secondary)
            ForEach(options, id: \.0) { option in
                Button {
                    selection = option.0
                } label: {
                    HStack(spacing: 14) {
                        Image(systemName: option.2).frame(width: 24)
                        Text(String(localized: String.LocalizationValue(option.1)))
                        Spacer()
                        Image(systemName: selection == option.0 ? "checkmark.circle.fill" : "circle")
                    }
                    .padding(18)
                    .foregroundStyle(AppTheme.Colors.label)
                    .background(selection == option.0 ? InitialExperienceStyle.accent.opacity(0.12) : AppTheme.Colors.cardBackground.opacity(0.8))
                    .clipShape(RoundedRectangle(cornerRadius: 16))
                    .overlay(RoundedRectangle(cornerRadius: 16).strokeBorder(selection == option.0 ? InitialExperienceStyle.accent : .clear))
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("onboarding-goal-\(option.0)")
                .accessibilityAddTraits(selection == option.0 ? .isSelected : [])
            }
            Spacer(minLength: 12)
            Button {
                var profile = appState.userProfile
                profile.goals = [selection]
                appState.updateUserProfile(profile, sync: true)
                next()
            } label: {
                Text(String(localized: "growth_find_words"))
                    .font(.headline).frame(maxWidth: .infinity).padding(18)
                    .foregroundStyle(.white).background(InitialExperienceStyle.accent)
                    .clipShape(RoundedRectangle(cornerRadius: 18))
            }
            .accessibilityIdentifier("onboarding-goal-continue")
            .padding(.bottom, 24)
        }
        .padding(.horizontal, 24)
        .foregroundStyle(AppTheme.Colors.label)
        .background(InitialExperienceStyle.background)
        .onAppear { selection = appState.userProfile.goals.first.flatMap { value in options.contains(where: { $0.0 == value }) ? value : nil } ?? "self_love" }
    }
}

struct FirstAffirmationStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState
    @StateObject private var likedStore = LikedQuotesStore()

    private var quote: Quote {
        let quoteIDs = ["self_love": "q013", "calm": "q021", "confidence": "q041", "letting_go": "q071"]
        let id = quoteIDs[appState.userProfile.goals.first ?? "self_love"] ?? "q013"
        return QuoteProvider.shared.byId(id, preferredLanguage: appState.effectiveLanguage)
            ?? QuoteProvider.shared.all(preferredLanguage: appState.effectiveLanguage)[0]
    }

    var body: some View {
        VStack(spacing: 24) {
            Text("Anicca").font(.system(size: 28, design: .serif)).padding(.top, 20)
            Spacer(minLength: 16)
            Image(systemName: "sun.max")
                .font(.system(size: 46, weight: .ultraLight))
                .foregroundStyle(InitialExperienceStyle.accent)
                .padding(24)
                .background(Circle().fill(AppTheme.Colors.habitAccent.opacity(0.2)))
                .accessibilityHidden(true)
            Text(String(localized: "growth_first_affirmation")).font(.caption).tracking(2).foregroundStyle(.secondary)
            Text(quote.text)
                .font(.system(.largeTitle, design: .serif))
                .multilineTextAlignment(.center).fixedSize(horizontal: false, vertical: true)
                .accessibilityIdentifier("onboarding-first-affirmation")
            Text(String(localized: "growth_first_subtitle"))
                .font(.subheadline).foregroundStyle(.secondary).multilineTextAlignment(.center)
            Button {
                likedStore.toggle(quote)
            } label: {
                Label(String(localized: likedStore.isLiked(quote.id) ? "growth_saved" : "growth_keep_close"),
                      systemImage: likedStore.isLiked(quote.id) ? "heart.fill" : "heart")
                    .font(.subheadline).padding(14)
                    .background(AppTheme.Colors.cardBackground.opacity(0.8))
                    .clipShape(Capsule())
            }
            .buttonStyle(.plain)
            .accessibilityIdentifier("onboarding-first-save")
            Spacer(minLength: 16)
            Button(action: next) {
                Text(String(localized: "growth_daily_moment"))
                    .font(.headline).frame(maxWidth: .infinity).padding(18)
                    .foregroundStyle(.white).background(InitialExperienceStyle.accent)
                    .clipShape(RoundedRectangle(cornerRadius: 18))
            }
            .accessibilityIdentifier("onboarding-first-continue")
            .padding(.bottom, 24)
        }
        .padding(.horizontal, 24)
        .foregroundStyle(AppTheme.Colors.label)
        .background(InitialExperienceStyle.background)
    }
}

struct ReminderScheduleStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            Text("Anicca").font(.system(size: 28, design: .serif)).padding(.top, 20)
            Spacer()
            Image(systemName: "bell.badge").font(.system(size: 40, weight: .ultraLight)).foregroundStyle(InitialExperienceStyle.accent)
                .accessibilityHidden(true)
            Text(String(localized: "growth_reminder_title")).font(.system(.largeTitle, design: .serif))
            Text(String(localized: "growth_reminder_explanation")).font(.subheadline).foregroundStyle(.secondary)
            Text(String(format: NSLocalizedString("growth_reminder_free_schedule", comment: ""), ReminderSchedule.slots(isPro: false).joined(separator: " · "))).font(.body)
            Text(String(format: NSLocalizedString("growth_reminder_pro_schedule", comment: ""), ReminderSchedule.slots(isPro: true).joined(separator: " · "))).font(.body)
            Text(TimeZone.current.identifier).font(.caption).foregroundStyle(.secondary)
            Spacer()
            Button(action: next) {
                Text(String(localized: "common_continue")).font(.headline)
                    .frame(maxWidth: .infinity).padding(18)
                    .foregroundStyle(.white).background(InitialExperienceStyle.accent)
                    .clipShape(RoundedRectangle(cornerRadius: 18))
            }
            .accessibilityIdentifier("onboarding-reminder-continue")
            .padding(.bottom, 24)
        }
        .padding(.horizontal, 24).foregroundStyle(AppTheme.Colors.label)
        .background(InitialExperienceStyle.background)
    }
}
