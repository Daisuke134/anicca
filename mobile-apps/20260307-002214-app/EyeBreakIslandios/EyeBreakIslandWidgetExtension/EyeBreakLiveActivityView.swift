import WidgetKit
import SwiftUI
import ActivityKit

struct EyeBreakLiveActivityView: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: EyeBreakAttributes.self) { context in
            LockScreenBannerView(context: context)
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.leading) {
                    Label("Eye Break", systemImage: "eye")
                }
                DynamicIslandExpandedRegion(.trailing) {
                    Text(formatTime(context.state.remainingSeconds))
                        .font(.title2.monospacedDigit())
                }
                DynamicIslandExpandedRegion(.bottom) {
                    Text("Breaks today: \(context.state.breakCount)")
                }
            } compactLeading: {
                Image(systemName: "eye")
            } compactTrailing: {
                Text(formatTime(context.state.remainingSeconds))
                    .font(.caption.monospacedDigit())
            } minimal: {
                Image(systemName: "eye")
            }
        }
    }

    private func formatTime(_ seconds: Int) -> String {
        let m = seconds / 60
        let s = seconds % 60
        return String(format: "%d:%02d", m, s)
    }
}

struct LockScreenBannerView: View {
    let context: ActivityViewContext<EyeBreakAttributes>

    var body: some View {
        HStack {
            Image(systemName: "eye")
                .font(.title2)
            VStack(alignment: .leading) {
                Text(context.state.timerState == "breaking" ? "Look away now" : "Next break in")
                    .font(.caption)
                Text(formatTime(context.state.remainingSeconds))
                    .font(.title.monospacedDigit().bold())
            }
            Spacer()
            Text("\(context.state.breakCount)")
                .font(.title2.bold())
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(.ultraThinMaterial)
                .clipShape(Capsule())
        }
        .padding()
    }

    private func formatTime(_ seconds: Int) -> String {
        let m = seconds / 60
        let s = seconds % 60
        return String(format: "%d:%02d", m, s)
    }
}
