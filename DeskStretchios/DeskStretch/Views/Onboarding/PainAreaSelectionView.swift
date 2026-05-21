import SwiftUI

struct PainAreaSelectionView: View {
    @Environment(AppState.self) private var appState
    let onNext: () -> Void

    private let columns = [
        GridItem(.flexible(), spacing: 16),
        GridItem(.flexible(), spacing: 16)
    ]

    var body: some View {
        VStack(spacing: 24) {
            VStack(spacing: 8) {
                Text(String(localized: "Where does it hurt?"))
                    .font(.title)
                    .fontWeight(.bold)

                Text(String(localized: "Select the areas you want to focus on."))
                    .font(.body)
                    .foregroundColor(.secondary)
            }
            .padding(.top, 32)

            LazyVGrid(columns: columns, spacing: 16) {
                ForEach(PainArea.allCases) { area in
                    PainAreaCard(
                        painArea: area,
                        isSelected: appState.selectedPainAreas.contains(area)
                    ) {
                        if appState.selectedPainAreas.contains(area) {
                            appState.selectedPainAreas.remove(area)
                        } else {
                            appState.selectedPainAreas.insert(area)
                        }
                    }
                }
            }

            Spacer()

            PrimaryButton(title: String(localized: "Continue")) {
                onNext()
            }
            .disabled(appState.selectedPainAreas.isEmpty)
            .opacity(appState.selectedPainAreas.isEmpty ? 0.5 : 1.0)
            .accessibilityIdentifier("onboarding_continue")
        }
        .padding(.horizontal, 24)
        .padding(.bottom, 32)
    }
}
