import SwiftUI
import SwiftData

struct HomeView: View {
    let viewModel: AppViewModel
    @Environment(\.modelContext) private var modelContext
    @Query(sort: \GratitudeEntry.date, order: .reverse) private var entries: [GratitudeEntry]

    @State private var gratitude1: String = ""
    @State private var gratitude2: String = ""
    @State private var gratitude3: String = ""
    @State private var showSavedFeedback: Bool = false
    @State private var affirmationBounce: Bool = false

    private var language: AppLanguage { viewModel.language }
    private var streak: Int { viewModel.calculateStreak(entries: entries) }
    private var hasTodayEntry: Bool { viewModel.hasTodayEntry(entries: entries) }

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                headerSection
                affirmationCard
                gratitudeInputSection
            }
            .padding(.horizontal, 16)
            .padding(.top, 8)
            .padding(.bottom, 32)
            .frame(maxWidth: 700)
            .frame(maxWidth: .infinity)
        }
        .scrollDismissesKeyboard(.interactively)
        .background(
            LinearGradient(
                colors: [Color(red: 1.0, green: 0.98, blue: 0.95), Color(red: 0.99, green: 0.94, blue: 0.88)],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()
        )
    }

    private var headerSection: some View {
        HStack(alignment: .top) {
            VStack(alignment: .leading, spacing: 4) {
                Text(L10n.greeting(for: language))
                    .font(.title.bold())

                Text(Date(), format: .dateTime.weekday(.wide).month(.wide).day())
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            if streak > 0 {
                VStack(spacing: 2) {
                    Text("🔥")
                        .font(.title)
                    Text("\(streak)")
                        .font(.title3.bold())
                        .foregroundStyle(Color(red: 0.83, green: 0.65, blue: 0.46))
                    Text(L10n.streakLabel(language))
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(Color(.secondarySystemGroupedBackground))
                .clipShape(.rect(cornerRadius: 14))
            }
        }
        .padding(.top, 8)
    }

    private var affirmationCard: some View {
        Button {
            withAnimation(.spring(duration: 0.4)) {
                viewModel.refreshAffirmation()
                affirmationBounce.toggle()
            }
        } label: {
            VStack(spacing: 16) {
                HStack {
                    Text(L10n.todaysAffirmation(language))
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(Color(red: 0.49, green: 0.71, blue: 0.62))
                        .textCase(.uppercase)
                        .tracking(1)
                    Spacer()
                    Image(systemName: "arrow.triangle.2.circlepath")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }

                Text(viewModel.currentAffirmation.text(for: language))
                    .font(.title3.weight(.medium))
                    .foregroundStyle(.primary)
                    .multilineTextAlignment(.leading)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .contentTransition(.numericText())

                Text(L10n.tapForNew(language))
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
            .padding(20)
            .background(
                RoundedRectangle(cornerRadius: 20)
                    .fill(.white.opacity(0.8))
                    .shadow(color: Color(red: 0.83, green: 0.65, blue: 0.46).opacity(0.12), radius: 12, y: 4)
            )
        }
        .buttonStyle(.plain)
        .sensoryFeedback(.impact(weight: .light), trigger: affirmationBounce)
    }

    private var gratitudeInputSection: some View {
        VStack(spacing: 16) {
            if hasTodayEntry {
                HStack(spacing: 8) {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(Color(red: 0.49, green: 0.71, blue: 0.62))
                    Text(L10n.alreadySaved(language))
                        .font(.subheadline.weight(.medium))
                        .foregroundStyle(Color(red: 0.49, green: 0.71, blue: 0.62))
                }
                .frame(maxWidth: .infinity)
                .padding(14)
                .background(Color(red: 0.49, green: 0.71, blue: 0.62).opacity(0.1))
                .clipShape(.rect(cornerRadius: 12))
            }

            VStack(spacing: 12) {
                gratitudeField(text: $gratitude1, number: 1)
                gratitudeField(text: $gratitude2, number: 2)
                gratitudeField(text: $gratitude3, number: 3)
            }

            Button {
                saveEntry()
            } label: {
                HStack(spacing: 8) {
                    if showSavedFeedback {
                        Image(systemName: "checkmark")
                            .font(.headline)
                    }
                    Text(showSavedFeedback ? (language == .english ? "Saved!" : "保存しました！") : L10n.save(language))
                        .font(.headline)
                }
                .foregroundStyle(.white)
                .frame(maxWidth: .infinity)
                .frame(height: 56)
                .background(
                    LinearGradient(
                        colors: canSave
                            ? [Color(red: 0.83, green: 0.65, blue: 0.46), Color(red: 0.76, green: 0.55, blue: 0.36)]
                            : [Color.gray.opacity(0.4), Color.gray.opacity(0.3)],
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )
                .clipShape(.rect(cornerRadius: 16))
            }
            .disabled(!canSave)
            .sensoryFeedback(.success, trigger: showSavedFeedback)
        }
    }

    private var canSave: Bool {
        !gratitude1.trimmingCharacters(in: .whitespaces).isEmpty ||
        !gratitude2.trimmingCharacters(in: .whitespaces).isEmpty ||
        !gratitude3.trimmingCharacters(in: .whitespaces).isEmpty
    }

    private func gratitudeField(text: Binding<String>, number: Int) -> some View {
        HStack(spacing: 12) {
            Text("\(number)")
                .font(.headline)
                .foregroundStyle(Color(red: 0.83, green: 0.65, blue: 0.46))
                .frame(width: 28, height: 28)
                .background(Color(red: 0.83, green: 0.65, blue: 0.46).opacity(0.15))
                .clipShape(Circle())

            TextField(L10n.gratefulPlaceholder(language), text: text, axis: .vertical)
                .font(.body)
                .lineLimit(1...3)
        }
        .padding(14)
        .background(Color(.secondarySystemGroupedBackground))
        .clipShape(.rect(cornerRadius: 14))
    }

    private func saveEntry() {
        let entry = GratitudeEntry(
            date: Date(),
            gratitude1: gratitude1.trimmingCharacters(in: .whitespaces),
            gratitude2: gratitude2.trimmingCharacters(in: .whitespaces),
            gratitude3: gratitude3.trimmingCharacters(in: .whitespaces),
            affirmation: viewModel.currentAffirmation.text(for: language)
        )
        modelContext.insert(entry)

        withAnimation(.spring(duration: 0.3)) {
            showSavedFeedback = true
        }

        gratitude1 = ""
        gratitude2 = ""
        gratitude3 = ""

        Task {
            try? await Task.sleep(for: .seconds(2))
            withAnimation { showSavedFeedback = false }
        }
    }
}
