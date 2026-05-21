import SwiftUI

struct TimerRing: View {
    let progress: Double  // 0.0 to 1.0
    let timeRemaining: String
    let lineWidth: CGFloat

    init(progress: Double, timeRemaining: String, lineWidth: CGFloat = 12) {
        self.progress = progress
        self.timeRemaining = timeRemaining
        self.lineWidth = lineWidth
    }

    var body: some View {
        ZStack {
            Circle()
                .stroke(Color.accentColor.opacity(0.15), lineWidth: lineWidth)

            Circle()
                .trim(from: 0, to: progress)
                .stroke(Color.accentColor, style: StrokeStyle(lineWidth: lineWidth, lineCap: .round))
                .rotationEffect(.degrees(-90))
                .animation(.easeInOut(duration: 0.3), value: progress)

            Text(timeRemaining)
                .font(.system(size: 48, weight: .light, design: .rounded))
                .monospacedDigit()
        }
    }
}
