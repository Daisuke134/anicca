import SwiftUI

struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(UserSettings.self) private var settings
    @State private var showPaywall = false

    var body: some View {
        NavigationStack {
            Form {
                Section("Focus Areas") {
                    ForEach(FocusArea.allCases) { area in
                        FocusAreaToggle(
                            area: area,
                            isSelected: settings.selectedFocusAreas.contains(area)
                        ) {
                            toggleFocusArea(area)
                        }
                    }
                }

                Section("Subscription") {
                    if SubscriptionService.shared.isPremium {
                        HStack {
                            Image(systemName: "crown.fill")
                                .foregroundColor(.yellow)
                            Text("Premium Active")
                                .foregroundColor(.secondary)
                        }
                    } else {
                        Button(action: { showPaywall = true }) {
                            HStack {
                                Image(systemName: "sparkles")
                                Text("Upgrade to Premium")
                            }
                        }
                    }

                    Button("Restore Purchases") {
                        Task {
                            try? await SubscriptionService.shared.restorePurchases()
                        }
                    }
                }

                Section("About") {
                    Link("Privacy Policy", destination: URL(string: "https://affirmflow.com/privacy")!)
                    Link("Terms of Service", destination: URL(string: "https://affirmflow.com/terms")!)

                    HStack {
                        Text("Version")
                        Spacer()
                        Text(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0")
                            .foregroundColor(.secondary)
                    }
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
            .sheet(isPresented: $showPaywall) {
                PaywallView()
            }
        }
    }

    private func toggleFocusArea(_ area: FocusArea) {
        var areas = settings.selectedFocusAreas
        if let index = areas.firstIndex(of: area) {
            areas.remove(at: index)
        } else if areas.count < 3 {
            areas.append(area)
        }
        settings.selectedFocusAreas = areas
        HapticsService.selection()
    }
}

struct FocusAreaToggle: View {
    let area: FocusArea
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                Image(systemName: area.systemImage)
                    .foregroundColor(area.color)
                Text(area.rawValue)
                    .foregroundColor(.primary)
                Spacer()
                if isSelected {
                    Image(systemName: "checkmark")
                        .foregroundColor(.purple)
                }
            }
        }
    }
}

#Preview {
    SettingsView()
        .environment(UserSettings())
}
