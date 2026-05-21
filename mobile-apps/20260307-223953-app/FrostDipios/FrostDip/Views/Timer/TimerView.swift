import SwiftUI
import SwiftData

struct TimerView: View {
    @State private var viewModel = TimerViewModel()
    @Environment(\.modelContext) private var modelContext

    var body: some View {
        NavigationStack {
            VStack(spacing: Theme.Spacing.lg) {
                Spacer()

                circularTimer

                heartRateDisplay

                temperatureInput

                actionButtons

                protocolInfo

                Spacer()
            }
            .padding(.horizontal, Theme.Spacing.md)
            .navigationTitle("Timer")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    protocolPicker
                }
            }
            .sheet(isPresented: $viewModel.showSummary) {
                if let session = viewModel.completedSession {
                    SessionSummaryView(session: session, onSave: { notes in
                        session.notes = notes
                        modelContext.insert(session)
                        let streak = StreakService()
                        streak.recordSession()
                        viewModel.dismissSummary()
                    }, onDelete: {
                        viewModel.dismissSummary()
                    })
                }
            }
        }
        .accessibilityIdentifier(AccessibilityID.timerView)
    }

    // MARK: - Circular Timer

    private var circularTimer: some View {
        ZStack {
            Circle()
                .stroke(Theme.Colors.cold.opacity(0.2), lineWidth: 12)

            Circle()
                .trim(from: 0, to: progress)
                .stroke(Theme.Colors.accent, style: StrokeStyle(lineWidth: 12, lineCap: .round))
                .rotationEffect(.degrees(-90))
                .animation(Theme.Animation.standard, value: progress)

            VStack(spacing: Theme.Spacing.xxs) {
                if viewModel.timerState == .breathing {
                    Text(breathPhaseText)
                        .font(Theme.Typography.title2)
                        .foregroundStyle(Theme.Colors.accent)
                        .accessibilityIdentifier(AccessibilityID.breathingPhaseLabel)
                } else {
                    Text(viewModel.formattedTime)
                        .font(Theme.Typography.timerDisplay)
                        .foregroundStyle(Theme.Colors.label)
                        .monospacedDigit()

                    Text("remaining")
                        .font(Theme.Typography.caption)
                        .foregroundStyle(Theme.Colors.secondaryLabel)
                }
            }
        }
        .frame(width: 250, height: 250)
        .accessibilityIdentifier(AccessibilityID.circularTimer)
    }

    private var progress: CGFloat {
        guard viewModel.selectedProtocol.coldTime > 0 else { return 0 }
        return viewModel.remainingTime / viewModel.selectedProtocol.coldTime
    }

    private var breathPhaseText: String {
        switch viewModel.breathPhase {
        case .inhale: return "Breathe In"
        case .hold: return "Hold"
        case .exhale: return "Breathe Out"
        }
    }

    // MARK: - Heart Rate

    private var heartRateDisplay: some View {
        Group {
            if let hr = viewModel.heartRate {
                HStack(spacing: Theme.Spacing.xxs) {
                    Image(systemName: "heart.fill")
                        .foregroundStyle(Theme.Colors.hot)
                    Text("\(Int(hr)) BPM")
                        .font(Theme.Typography.headline)
                }
                .accessibilityIdentifier(AccessibilityID.timerHrDisplay)
            }
        }
    }

    // MARK: - Temperature

    private var temperatureInput: some View {
        HStack {
            Image(systemName: "thermometer.medium")
                .foregroundStyle(Theme.Colors.cold)
            Text("Water Temp")
                .font(Theme.Typography.subheadline)
            Spacer()
            Stepper(
                value: Binding(
                    get: { viewModel.waterTemperature ?? 4.0 },
                    set: { viewModel.waterTemperature = $0 }
                ),
                in: 0...20,
                step: 0.5
            ) {
                Text("\(viewModel.waterTemperature.map { String(format: "%.1f", $0) } ?? "--")\u{00B0}C")
                    .font(Theme.Typography.body)
                    .monospacedDigit()
            }
        }
        .padding(Theme.Spacing.sm)
        .background(Theme.Colors.secondaryBackground)
        .clipShape(RoundedRectangle(cornerRadius: Theme.CornerRadius.medium))
        .accessibilityIdentifier(AccessibilityID.timerTemperatureInput)
    }

    // MARK: - Action Buttons

    private var actionButtons: some View {
        HStack(spacing: Theme.Spacing.md) {
            switch viewModel.timerState {
            case .idle:
                Button {
                    viewModel.startBreathingPrep()
                } label: {
                    Label("Prep", systemImage: "wind")
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(.bordered)
                .tint(Theme.Colors.cold)
                .accessibilityIdentifier(AccessibilityID.timerBreathingPrep)

                Button {
                    viewModel.startTimer()
                } label: {
                    Label("Start", systemImage: "play.fill")
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(.borderedProminent)
                .tint(Theme.Colors.accent)
                .accessibilityIdentifier(AccessibilityID.timerStart)

            case .breathing:
                Button {
                    viewModel.skipBreathingPrep()
                } label: {
                    Label("Skip", systemImage: "forward.fill")
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(.bordered)
                .accessibilityIdentifier(AccessibilityID.breathingSkip)

            case .running:
                Button {
                    viewModel.pauseTimer()
                } label: {
                    Label("Pause", systemImage: "pause.fill")
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(.bordered)
                .tint(Theme.Colors.warning)
                .accessibilityIdentifier(AccessibilityID.timerPause)

                Button {
                    viewModel.stopTimer()
                } label: {
                    Label("Stop", systemImage: "stop.fill")
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(.borderedProminent)
                .tint(Theme.Colors.destructive)
                .accessibilityIdentifier(AccessibilityID.timerStop)

            case .paused:
                Button {
                    viewModel.resumeTimer()
                } label: {
                    Label("Resume", systemImage: "play.fill")
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(.borderedProminent)
                .tint(Theme.Colors.success)
                .accessibilityIdentifier(AccessibilityID.timerStart)

                Button {
                    viewModel.stopTimer()
                } label: {
                    Label("Stop", systemImage: "stop.fill")
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(.bordered)
                .tint(Theme.Colors.destructive)
                .accessibilityIdentifier(AccessibilityID.timerStop)

            case .completed:
                EmptyView()
            }
        }
    }

    // MARK: - Protocol Info

    private var protocolInfo: some View {
        VStack(spacing: Theme.Spacing.xxs) {
            Text("Protocol: \(viewModel.selectedProtocol.name)")
                .font(Theme.Typography.subheadline)
                .foregroundStyle(Theme.Colors.secondaryLabel)

            let duration = Int(viewModel.selectedProtocol.coldTime)
            Text("\(duration / 60):\(String(format: "%02d", duration % 60))")
                .font(Theme.Typography.caption)
                .foregroundStyle(Theme.Colors.secondaryLabel)
        }
    }

    // MARK: - Protocol Picker

    private var protocolPicker: some View {
        Menu {
            ForEach(viewModel.availableProtocols, id: \.name) { proto in
                Button(proto.name) {
                    viewModel.selectProtocol(proto)
                }
            }
        } label: {
            Image(systemName: "snowflake")
                .foregroundStyle(Theme.Colors.accent)
        }
        .accessibilityIdentifier(AccessibilityID.timerProtocolSelector)
    }
}
