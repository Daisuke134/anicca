import SwiftUI
import WidgetKit

struct SmallWidgetView: View {
    let entry: AffirmationEntry

    var body: some View {
        VStack(spacing: 8) {
            Text(entry.affirmation)
                .font(.caption)
                .fontWeight(.medium)
                .lineLimit(4)
                .multilineTextAlignment(.center)

            HStack(spacing: 4) {
                Image(systemName: entry.focusArea.systemImage)
                    .foregroundColor(entry.focusArea.color)
                    .font(.caption2)
            }
        }
        .padding(12)
        .containerBackground(.fill.tertiary, for: .widget)
    }
}
