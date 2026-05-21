import SwiftUI

struct SessionView: View {
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @Environment(\.presentationMode) var presentationMode
    @State private var selectedType: BreathingType = .box
    @State private var selectedDuration: SessionDuration = .short
    @State private var isRunning = false
    @State private var showFeedback = false
    @State private var timeRemaining = 60
    @State private var timer: Timer?
    @State private var currentPhaseIndex = 0
    @State private var phaseTimeRemaining: Double = 0
    @State private var circleScale: CGFloat = 1.0

    var body: some View {
        ZStack {
            Color(hex: "#0a1628").ignoresSafeArea()

            if showFeedback {
                feedbackView
            } else if isRunning {
                runningView
            } else {
                selectionView
            }
        }
        .onDisappear { timer?.invalidate() }
    }

    private var selectionView: some View {
        VStack(spacing: 24) {
            Text(L10n.sessionTitle)
                .font(.system(size: 24, weight: .bold))
                .foregroundColor(.white)
                .padding(.top, 24)

            // Breathing type selection
            VStack(spacing: 8) {
                ForEach(BreathingType.allCases) { type in
                    let isLocked = type != .box && !subscriptionManager.isPro
                    Button {
                        if !isLocked { selectedType = type }
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text(type.localizedName)
                                        .font(.system(size: 15, weight: .medium))
                                        .foregroundColor(isLocked ? Color(hex: "#6b7280") : .white)
                                    if isLocked {
                                        Image(systemName: "lock.fill")
                                            .font(.system(size: 12))
                                            .foregroundColor(Color(hex: "#6b7280"))
                                    }
                                }
                                Text(type.description)
                                    .font(.system(size: 13))
                                    .foregroundColor(Color(hex: "#6b7280"))
                            }
                            Spacer()
                            if selectedType == type {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundColor(Color(hex: "#2dd4bf"))
                            }
                        }
                        .padding(14)
                        .background(selectedType == type ? Color(hex: "#1e4d6b").opacity(0.5) : Color(hex: "#111827"))
                        .cornerRadius(10)
                    }
                }
            }
            .padding(.horizontal, 24)

            // Duration selection
            HStack(spacing: 12) {
                ForEach(SessionDuration.allCases, id: \.rawValue) { dur in
                    Button {
                        selectedDuration = dur
                        timeRemaining = dur.rawValue
                    } label: {
                        Text(dur.label)
                            .font(.system(size: 15, weight: .medium))
                            .foregroundColor(selectedDuration == dur ? Color(hex: "#0a1628") : .white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 10)
                            .background(selectedDuration == dur ? Color(hex: "#2dd4bf") : Color(hex: "#111827"))
                            .cornerRadius(10)
                    }
                }
            }
            .padding(.horizontal, 24)

            Spacer()

            Button {
                startSession()
            } label: {
                Text(L10n.isJapaneseLang ? "セッション開始" : "Start Session")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                    .background(Color(hex: "#2dd4bf"))
                    .cornerRadius(14)
            }
            .padding(.horizontal, 24)

            Spacer().frame(height: 32)
        }
    }

    private var runningView: some View {
        VStack(spacing: 32) {
            HStack {
                Spacer()
                Text("\(timeRemaining)s")
                    .font(.system(size: 18, weight: .medium))
                    .foregroundColor(Color(hex: "#9ca3af"))
                    .padding(.trailing, 24)
            }
            .padding(.top, 24)

            Spacer()

            ZStack {
                Circle()
                    .fill(Color(hex: "#1e4d6b").opacity(0.3))
                    .frame(width: 220, height: 220)
                    .scaleEffect(circleScale)

                Circle()
                    .fill(Color(hex: "#2dd4bf").opacity(0.7))
                    .frame(width: 150, height: 150)
                    .scaleEffect(circleScale)

                VStack(spacing: 4) {
                    Text(currentPhase.label)
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundColor(.white)
                    Text(String(format: "%.0f", phaseTimeRemaining))
                        .font(.system(size: 36, weight: .bold))
                        .foregroundColor(.white)
                }
            }

            Text(selectedType.localizedName)
                .font(.system(size: 15))
                .foregroundColor(Color(hex: "#9ca3af"))

            Spacer()

            Button {
                stopSession()
            } label: {
                Text(L10n.isJapaneseLang ? "終了" : "Stop")
                    .font(.system(size: 16))
                    .foregroundColor(Color(hex: "#6b7280"))
            }
            .padding(.bottom, 32)
        }
    }

    private var feedbackView: some View {
        VStack(spacing: 32) {
            Spacer()

            Text("✨")
                .font(.system(size: 60))

            Text(L10n.sessionComplete)
                .font(.system(size: 24, weight: .bold))
                .foregroundColor(.white)

            Text(L10n.sessionFeedbackTitle)
                .font(.system(size: 18))
                .foregroundColor(Color(hex: "#9ca3af"))

            HStack(spacing: 16) {
                feedbackButton(label: L10n.sessionFeedbackBetter, feltBetter: true)
                feedbackButton(label: L10n.sessionFeedbackSame, feltBetter: false)
            }
            .padding(.horizontal, 24)

            Spacer()
        }
    }

    private func feedbackButton(label: String, feltBetter: Bool) -> some View {
        Button {
            var record = SessionRecord(
                breathingType: selectedType,
                durationSec: selectedDuration.rawValue
            )
            record.feltBetter = feltBetter
            SessionStore.shared.save(record)
            AnalyticsManager.shared.trackSessionCompleted(
                breathingType: selectedType,
                durationSec: selectedDuration.rawValue,
                feltBetter: feltBetter
            )
            presentationMode.wrappedValue.dismiss()
        } label: {
            Text(label)
                .font(.system(size: 16, weight: .medium))
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .background(Color(hex: "#111827"))
                .cornerRadius(12)
        }
    }

    private var currentPhase: BreathingPhase {
        let phases = selectedType.phases
        return phases[currentPhaseIndex % phases.count]
    }

    private func startSession() {
        isRunning = true
        timeRemaining = selectedDuration.rawValue
        currentPhaseIndex = 0
        phaseTimeRemaining = selectedType.phases[0].duration
        startCircleAnimation()
        AnalyticsManager.shared.trackSessionStarted(
            breathingType: selectedType,
            durationSec: selectedDuration.rawValue
        )

        timer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { _ in
            timeRemaining = max(0, timeRemaining - 1)

            if timeRemaining <= 0 {
                timer?.invalidate()
                isRunning = false
                showFeedback = true
                return
            }

            phaseTimeRemaining -= 0.1
            if phaseTimeRemaining <= 0 {
                currentPhaseIndex += 1
                let phases = selectedType.phases
                phaseTimeRemaining = phases[currentPhaseIndex % phases.count].duration
                updateCircleAnimation()
            }
        }
    }

    private func stopSession() {
        timer?.invalidate()
        isRunning = false
    }

    private func startCircleAnimation() {
        updateCircleAnimation()
    }

    private func updateCircleAnimation() {
        let phase = currentPhase
        withAnimation(.easeInOut(duration: phase.duration)) {
            switch phase.type {
            case .inhale:
                circleScale = 1.4
            case .exhale:
                circleScale = 0.8
            case .hold:
                break
            }
        }
    }
}
