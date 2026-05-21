import SwiftUI

struct SettingsView: View {
    @Environment(AppState.self) private var appState
    @State private var showTimerSettings = false

    var body: some View {
        NavigationStack {
            Form {
                Section(String(localized: "Timer")) {
                    Button {
                        showTimerSettings = true
                    } label: {
                        HStack {
                            Text(String(localized: "Break Interval"))
                            Spacer()
                            Text(String(localized: "\(appState.breakSchedule.intervalMinutes) min"))
                                .foregroundColor(.secondary)
                        }
                    }
                    .foregroundColor(.primary)
                }

                Section(String(localized: "Pain Areas")) {
                    ForEach(PainArea.allCases) { area in
                        Toggle(area.displayName, isOn: Binding(
                            get: { appState.selectedPainAreas.contains(area) },
                            set: { isOn in
                                if isOn {
                                    appState.selectedPainAreas.insert(area)
                                } else {
                                    appState.selectedPainAreas.remove(area)
                                }
                                appState.persistPainAreas()
                            }
                        ))
                    }
                }

                Section(String(localized: "Subscription")) {
                    if appState.isPremium {
                        HStack {
                            Text(String(localized: "Status"))
                            Spacer()
                            Text(String(localized: "Premium"))
                                .foregroundColor(.green)
                        }
                    } else {
                        Button(String(localized: "Upgrade to Premium")) {
                            // Handled via PaywallView
                        }
                    }

                    Button(String(localized: "Restore Purchases")) {
                        Task {
                            let success = try? await SubscriptionService.shared.restorePurchases()
                            if success == true {
                                appState.isPremium = true
                            }
                        }
                    }
                }

                Section(String(localized: "Legal")) {
                    Link(String(localized: "Privacy Policy"),
                         destination: URL(string: "https://aniccaai.com/privacy")!)
                    Link(String(localized: "Terms of Use"),
                         destination: URL(string: "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/")!)
                }
            }
            .navigationTitle(String(localized: "Settings"))
            .sheet(isPresented: $showTimerSettings) {
                TimerSettingsSheet()
            }
        }
    }
}
