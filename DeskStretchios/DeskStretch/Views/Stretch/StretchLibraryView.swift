import SwiftUI

struct StretchLibraryView: View {
    @Environment(AppState.self) private var appState
    @State private var selectedCategory: PainArea?
    @State private var showPaywall = false

    private let libraryService = StretchLibraryService()

    var filteredExercises: [StretchExercise] {
        if let category = selectedCategory {
            return libraryService.exercises(for: [category])
        }
        return libraryService.all
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        FilterChip(
                            title: String(localized: "All"),
                            isSelected: selectedCategory == nil
                        ) {
                            selectedCategory = nil
                        }

                        ForEach(PainArea.allCases) { area in
                            FilterChip(
                                title: area.displayName,
                                isSelected: selectedCategory == area
                            ) {
                                selectedCategory = area
                            }
                        }
                    }
                    .padding(.horizontal)
                    .padding(.vertical, 12)
                }

                List(filteredExercises) { exercise in
                    let isLocked = exercise.isPremium && !appState.isPremium
                    ExerciseCard(exercise: exercise, isPremium: exercise.isPremium, isLocked: isLocked)
                        .listRowSeparator(.hidden)
                        .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
                        .onTapGesture {
                            if isLocked {
                                showPaywall = true
                            }
                        }
                }
                .listStyle(.plain)
            }
            .navigationTitle(String(localized: "Stretch Library"))
            .onAppear { libraryService.loadFromBundle() }
            .sheet(isPresented: $showPaywall) {
                PaywallView(onDismiss: { showPaywall = false })
            }
        }
    }
}
