// File: Views/Workout/WorkoutTimerView.swift
// SCR-007: Workout timer with Zone 2 HR guide
// F-003: Manual workout logging with background timer support

import SwiftUI
import SwiftData

struct WorkoutTimerView: View {
    @Environment(\.modelContext) private var modelContext
    @Query private var profiles: [UserProfile]
    @State private var viewModel = WorkoutViewModel()
    @State private var savedSession: WorkoutSession? = nil
    @State private var showLog = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 32) {
                if let profile = profiles.first {
                    hrGuide(profile: profile)
                }

                timerDisplay

                zone2TimeDisplay

                controlButtons
            }
            .padding()
            .navigationTitle("Workout")
        }
        .accessibilityIdentifier("screen_workout")
        .onDisappear { viewModel.stopTimer() }
        .sheet(item: $savedSession) { session in
            WorkoutLogView(session: session)
        }
    }

    private func hrGuide(profile: UserProfile) -> some View {
        VStack(spacing: 4) {
            Text("Zone 2 Target HR")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text("\(Zone2Calculator.zone2MinHR(age: profile.age))–\(Zone2Calculator.zone2MaxHR(age: profile.age)) bpm")
                .font(.largeTitle.bold())
                .foregroundStyle(.brandPrimary)
                .accessibilityIdentifier("workout_zone2_range")
        }
    }

    private var timerDisplay: some View {
        Text(viewModel.formattedTime)
            .font(.system(size: 64, weight: .bold, design: .monospaced))
            .accessibilityIdentifier("label_timer")
    }

    private var zone2TimeDisplay: some View {
        let z2Min = viewModel.zone2Seconds / 60
        let z2Sec = viewModel.zone2Seconds % 60
        return Text("Zone 2: \(String(format: "%02d:%02d", z2Min, z2Sec))")
            .font(.title3)
            .foregroundStyle(.secondary)
            .accessibilityIdentifier("label_zone2_time")
    }

    private var controlButtons: some View {
        Group {
            if viewModel.isRunning {
                Button("Stop") {
                    let age = profiles.first?.age ?? 30
                    let elapsed = viewModel.elapsedSeconds
                    let zone2 = viewModel.zone2Seconds
                    let hr = Zone2Calculator.zone2MaxHR(age: age)
                    viewModel.stopAndSave(modelContext: modelContext, age: age)

                    savedSession = WorkoutSession(
                        durationSeconds: elapsed,
                        zone2Seconds: zone2,
                        targetHR: hr
                    )
                }
                .buttonStyle(.borderedProminent)
                .tint(.brandDanger)
                .accessibilityIdentifier("btn_stop_workout")
            } else {
                Button("Start Zone 2") {
                    viewModel.startTimer()
                }
                .buttonStyle(.borderedProminent)
                .tint(.brandPrimary)
                .accessibilityIdentifier("btn_start_workout")
            }
        }
    }
}
