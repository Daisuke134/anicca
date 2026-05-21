import SwiftUI

struct TimerSettingsSheet: View {
    @Environment(AppState.self) private var appState
    @Environment(\.dismiss) private var dismiss

    private let intervals = [30, 45, 60, 90]

    var body: some View {
        NavigationStack {
            Form {
                Section(String(localized: "Break Interval")) {
                    ForEach(intervals, id: \.self) { minutes in
                        Button {
                            appState.breakSchedule.intervalMinutes = minutes
                            appState.persistBreakSchedule()
                        } label: {
                            HStack {
                                Text(String(localized: "\(minutes) minutes"))
                                Spacer()
                                if appState.breakSchedule.intervalMinutes == minutes {
                                    Image(systemName: "checkmark")
                                        .foregroundColor(.accentColor)
                                }
                            }
                        }
                        .foregroundColor(.primary)
                    }
                }

                Section(String(localized: "Notifications")) {
                    Toggle(String(localized: "Break Reminders"), isOn: Binding(
                        get: { appState.breakSchedule.isEnabled },
                        set: { newValue in
                            appState.breakSchedule.isEnabled = newValue
                            appState.persistBreakSchedule()
                        }
                    ))
                }
            }
            .navigationTitle(String(localized: "Timer Settings"))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(String(localized: "Done")) { dismiss() }
                }
            }
        }
    }
}
