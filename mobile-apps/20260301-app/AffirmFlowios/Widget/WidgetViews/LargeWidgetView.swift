import SwiftUI
import WidgetKit

struct LargeWidgetView: View {
    let entry: AffirmationEntry

    var body: some View {
        VStack(spacing: 16) {
            Spacer()

            Image(systemName: entry.focusArea.systemImage)
                .font(.system(size: 40))
                .foregroundColor(entry.focusArea.color)

            Text(entry.affirmation)
                .font(.title2)
                .fontWeight(.semibold)
                .multilineTextAlignment(.center)
                .lineLimit(5)

            Text(entry.focusArea.rawValue)
                .font(.caption)
                .foregroundColor(.secondary)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(entry.focusArea.color.opacity(0.2))
                .cornerRadius(8)

            Spacer()

            HStack {
                Spacer()
                Button(intent: RefreshAffirmationIntent()) {
                    HStack {
                        Image(systemName: "arrow.clockwise")
                        Text("Refresh")
                    }
                    .font(.caption)
                    .foregroundColor(.purple)
                }
                .buttonStyle(.plain)
            }
        }
        .padding()
        .containerBackground(.fill.tertiary, for: .widget)
    }
}
