import SwiftUI

struct FocusAreaSelectionView: View {
    @Environment(UserSettings.self) private var settings
    @State private var selectedAreas: Set<FocusArea> = []
    let onContinue: () -> Void

    var body: some View {
        VStack(spacing: Spacing.lg) {
            VStack(spacing: Spacing.sm) {
                Text("Choose Your Focus")
                    .font(.title)
                    .fontWeight(.bold)

                Text("Select up to 3 areas")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            .padding(.top, Spacing.xxl)

            ScrollView {
                VStack(spacing: Spacing.md) {
                    ForEach(FocusArea.allCases) { area in
                        FocusAreaCard(
                            area: area,
                            isSelected: selectedAreas.contains(area)
                        ) {
                            toggleSelection(area)
                        }
                    }
                }
                .padding(.horizontal, Spacing.lg)
            }

            Button(action: {
                settings.selectedFocusAreas = Array(selectedAreas)
                onContinue()
            }) {
                Text("Continue")
                    .font(.headline)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(selectedAreas.isEmpty ? Color.gray : Color.purple)
                    .cornerRadius(CornerRadius.medium)
            }
            .disabled(selectedAreas.isEmpty)
            .padding(.horizontal, Spacing.xl)
            .padding(.bottom, Spacing.xl)
        }
    }

    private func toggleSelection(_ area: FocusArea) {
        HapticsService.selection()
        if selectedAreas.contains(area) {
            selectedAreas.remove(area)
        } else if selectedAreas.count < 3 {
            selectedAreas.insert(area)
        }
    }
}

struct FocusAreaCard: View {
    let area: FocusArea
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: Spacing.md) {
                Image(systemName: area.systemImage)
                    .font(.title2)
                    .foregroundColor(area.color)
                    .frame(width: 32)

                VStack(alignment: .leading, spacing: Spacing.xxs) {
                    Text(area.rawValue)
                        .font(.headline)
                        .foregroundColor(.primary)

                    Text(area.description)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }

                Spacer()

                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.purple)
                        .font(.title2)
                }
            }
            .padding(Spacing.md)
            .background(isSelected ? Color.purple.opacity(0.1) : Color(.systemBackground))
            .cornerRadius(CornerRadius.large)
            .overlay(
                RoundedRectangle(cornerRadius: CornerRadius.large)
                    .stroke(isSelected ? Color.purple : Color.gray.opacity(0.2), lineWidth: isSelected ? 2 : 1)
            )
        }
        .buttonStyle(.plain)
    }
}

#Preview {
    FocusAreaSelectionView(onContinue: {})
        .environment(UserSettings())
}
