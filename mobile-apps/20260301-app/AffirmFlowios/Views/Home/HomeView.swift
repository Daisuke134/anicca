import SwiftUI
import SwiftData
import WidgetKit

struct HomeView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(UserSettings.self) private var settings
    @Environment(AffirmationService.self) private var affirmationService

    @Query(sort: \Affirmation.createdAt, order: .reverse)
    private var allAffirmations: [Affirmation]

    @State private var currentAffirmation: Affirmation?
    @State private var isLoading = false
    @State private var showPaywall = false
    @State private var showSettings = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            VStack(spacing: Spacing.lg) {
                Spacer()

                // Affirmation Card
                AffirmationCardView(
                    affirmation: currentAffirmation,
                    isLoading: isLoading,
                    errorMessage: errorMessage
                )

                // Action Buttons
                HStack(spacing: Spacing.xxl) {
                    ActionButton(
                        systemImage: currentAffirmation?.isFavorite == true ? "heart.fill" : "heart",
                        color: .pink,
                        action: toggleFavorite
                    )

                    ActionButton(
                        systemImage: canRefresh ? "arrow.clockwise" : "lock.fill",
                        color: canRefresh ? .purple : .gray,
                        action: refresh
                    )
                }

                Spacer()

                // Navigation
                HStack(spacing: Spacing.xxl) {
                    NavigationLink(destination: HistoryView()) {
                        VStack {
                            Image(systemName: "clock.arrow.circlepath")
                                .font(.title2)
                            Text("History")
                                .font(.caption)
                        }
                        .foregroundColor(.secondary)
                    }

                    NavigationLink(destination: FavoritesView()) {
                        VStack {
                            Image(systemName: "star.fill")
                                .font(.title2)
                            Text("Favorites")
                                .font(.caption)
                        }
                        .foregroundColor(.secondary)
                    }
                }

                // Status
                if !SubscriptionService.shared.isPremium {
                    Button(action: { showPaywall = true }) {
                        Text("\(settings.refreshesRemaining) of \(UserSettings.freeLimit) today - Upgrade")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .padding(.bottom, Spacing.md)
                }
            }
            .padding()
            .navigationTitle("")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(action: { showSettings = true }) {
                        Image(systemName: "gearshape")
                    }
                }
            }
            .sheet(isPresented: $showPaywall) {
                PaywallView()
            }
            .sheet(isPresented: $showSettings) {
                SettingsView()
            }
            .task {
                if currentAffirmation == nil {
                    await generateInitialAffirmation()
                }
            }
        }
    }

    private var canRefresh: Bool {
        SubscriptionService.shared.isPremium || settings.canRefresh
    }

    private func generateInitialAffirmation() async {
        // Use most recent if exists today
        if let recent = allAffirmations.first,
           Calendar.current.isDateInToday(recent.createdAt) {
            currentAffirmation = recent
            return
        }

        await generateNewAffirmation()
    }

    private func refresh() {
        if !canRefresh {
            showPaywall = true
            return
        }

        Task {
            await generateNewAffirmation()
            if !SubscriptionService.shared.isPremium {
                settings.incrementRefreshCount()
            }
        }
    }

    private func generateNewAffirmation() async {
        isLoading = true
        errorMessage = nil

        guard let focusArea = settings.selectedFocusAreas.randomElement() else {
            errorMessage = "Please select focus areas in Settings"
            isLoading = false
            return
        }

        do {
            let content = try await affirmationService.generateAffirmation(for: focusArea)
            let affirmation = Affirmation(content: content, focusArea: focusArea)
            modelContext.insert(affirmation)
            currentAffirmation = affirmation
            HapticsService.success()

            // Update widget
            saveForWidget(content: content, focusArea: focusArea)
        } catch {
            errorMessage = error.localizedDescription
            HapticsService.error()
        }

        isLoading = false
    }

    private func toggleFavorite() {
        guard let affirmation = currentAffirmation else { return }
        affirmation.isFavorite.toggle()
        HapticsService.selection()
    }

    private func saveForWidget(content: String, focusArea: FocusArea) {
        let defaults = UserDefaults.standard
        defaults.set(content, forKey: "currentAffirmation")
        defaults.set(focusArea.rawValue, forKey: "currentFocusArea")

        // Refresh widget
        WidgetCenter.shared.reloadAllTimelines()
    }
}

struct ActionButton: View {
    let systemImage: String
    let color: Color
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .font(.title)
                .foregroundColor(color)
                .frame(width: 60, height: 60)
                .background(color.opacity(0.1))
                .clipShape(Circle())
        }
    }
}

#Preview {
    HomeView()
        .environment(UserSettings())
        .environment(AffirmationService())
}
