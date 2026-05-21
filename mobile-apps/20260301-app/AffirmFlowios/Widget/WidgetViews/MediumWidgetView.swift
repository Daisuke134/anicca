import SwiftUI
import WidgetKit

struct MediumWidgetView: View {
    let entry: AffirmationEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(entry.affirmation)
                .font(.headline)
                .lineLimit(3)

            HStack {
                Image(systemName: entry.focusArea.systemImage)
                    .foregroundColor(entry.focusArea.color)
                Text(entry.focusArea.rawValue)
                    .font(.caption)
                    .foregroundColor(.secondary)

                Spacer()

                // Refresh button via App Intent
                Button(intent: RefreshAffirmationIntent()) {
                    Image(systemName: "arrow.clockwise")
                        .foregroundColor(.purple)
                }
                .buttonStyle(.plain)
            }
        }
        .padding()
        .containerBackground(.fill.tertiary, for: .widget)
    }
}
