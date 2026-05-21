// File: Views/Workout/WorkoutLogView.swift
// SCR-008: Post-workout log entry with zone2 minutes input
// F-003: Zone 2 manual workout logging
// UX_SPEC §7: input_zone2_minutes (TextField)

import SwiftUI
import SwiftData

struct WorkoutLogView: View {
    let session: WorkoutSession
    @Environment(\.dismiss) private var dismiss
    @State private var zone2MinutesInput: Int

    init(session: WorkoutSession) {
        self.session = session
        _zone2MinutesInput = State(initialValue: max(0, Int(session.zone2Minutes)))
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: Spacing.lg) {
                summaryCard

                Text("Workout saved!")
                    .font(.displayMedium)
                    .accessibilityIdentifier("label_workout_saved")

                zone2InputSection

                Button("Save Workout") { dismiss() }
                    .buttonStyle(.borderedProminent)
                    .tint(.brandPrimary)
                    .accessibilityIdentifier("btn_save_workout")
            }
            .padding(Spacing.lg)
            .navigationTitle("Workout Summary")
            .navigationBarTitleDisplayMode(.inline)
        }
        .accessibilityIdentifier("screen_workout_log")
    }

    private var summaryCard: some View {
        VStack(spacing: Spacing.md) {
            HStack {
                statItem(
                    label: "Duration",
                    value: formatDuration(session.durationSeconds),
                    id: "log_duration"
                )
                Divider()
                statItem(
                    label: "Zone 2 %",
                    value: String(format: "%.0f%%", session.zone2Percentage),
                    id: "log_zone2_percent"
                )
            }
            .frame(maxWidth: .infinity)
        }
        .padding(Spacing.md)
        .background(Color.surfaceCard)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var zone2InputSection: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            Text("Zone 2 Time (minutes)")
                .font(.headlineMedium)
                .foregroundStyle(Color.textPrimary)
            Stepper("\(zone2MinutesInput) min", value: $zone2MinutesInput, in: 0...240)
                .accessibilityIdentifier("input_zone2_minutes")
        }
        .padding(Spacing.md)
        .background(Color.surfaceCard)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private func statItem(label: String, value: String, id: String) -> some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.title3.bold())
                .accessibilityIdentifier(id)
            Text(label)
                .font(.labelSmall)
                .foregroundStyle(Color.textSecondary)
        }
        .frame(maxWidth: .infinity)
    }

    private func formatDuration(_ seconds: Int) -> String {
        let m = seconds / 60
        let s = seconds % 60
        return String(format: "%d:%02d", m, s)
    }
}
