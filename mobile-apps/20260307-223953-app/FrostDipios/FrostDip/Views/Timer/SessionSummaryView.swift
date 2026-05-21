import SwiftUI

struct SessionSummaryView: View {
    let session: PlungeSession
    let onSave: (String) -> Void
    let onDelete: () -> Void

    @State private var notes = ""

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: Theme.Spacing.lg) {
                    headerSection
                    statsSection
                    notesSection
                }
                .padding(Theme.Spacing.md)
            }
            .navigationTitle("Session Complete")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") {
                        onSave(notes)
                    }
                    .accessibilityIdentifier(AccessibilityID.sessionSummarySave)
                }
                ToolbarItem(placement: .cancellationAction) {
                    Button("Delete", role: .destructive) {
                        onDelete()
                    }
                }
            }
        }
        .accessibilityIdentifier(AccessibilityID.sessionSummaryView)
    }

    // MARK: - Header

    private var headerSection: some View {
        VStack(spacing: Theme.Spacing.xs) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 60))
                .foregroundStyle(Theme.Colors.success)

            Text("Great job!")
                .font(Theme.Typography.title)
        }
        .padding(.top, Theme.Spacing.lg)
    }

    // MARK: - Stats

    private var statsSection: some View {
        VStack(spacing: Theme.Spacing.sm) {
            statRow(icon: "timer", label: "Duration", value: formattedDuration)
                .accessibilityIdentifier(AccessibilityID.sessionSummaryDuration)

            if let temp = session.waterTemperature {
                statRow(icon: "thermometer.medium", label: "Temperature", value: String(format: "%.1f\u{00B0}C", temp))
                    .accessibilityIdentifier(AccessibilityID.sessionSummaryTemp)
            }

            if let avgHR = session.heartRateAvg {
                statRow(icon: "heart.fill", label: "Avg Heart Rate", value: "\(Int(avgHR)) BPM")
                    .accessibilityIdentifier(AccessibilityID.sessionSummaryHr)
            }

            if let proto = session.protocolName {
                statRow(icon: "snowflake", label: "Protocol", value: proto)
            }
        }
        .padding(Theme.Spacing.md)
        .background(Theme.Colors.secondaryBackground)
        .clipShape(RoundedRectangle(cornerRadius: Theme.CornerRadius.large))
    }

    private func statRow(icon: String, label: String, value: String) -> some View {
        HStack {
            Image(systemName: icon)
                .foregroundStyle(Theme.Colors.accent)
                .frame(width: 24)
            Text(label)
                .font(Theme.Typography.subheadline)
                .foregroundStyle(Theme.Colors.secondaryLabel)
            Spacer()
            Text(value)
                .font(Theme.Typography.headline)
        }
    }

    // MARK: - Notes

    private var notesSection: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
            Text("Notes")
                .font(Theme.Typography.headline)

            TextField("How did it feel?", text: $notes, axis: .vertical)
                .lineLimit(3...6)
                .textFieldStyle(.roundedBorder)
                .accessibilityIdentifier(AccessibilityID.sessionSummaryNotes)
        }
    }

    private var formattedDuration: String {
        let minutes = Int(session.duration) / 60
        let seconds = Int(session.duration) % 60
        return "\(minutes):\(String(format: "%02d", seconds))"
    }
}
