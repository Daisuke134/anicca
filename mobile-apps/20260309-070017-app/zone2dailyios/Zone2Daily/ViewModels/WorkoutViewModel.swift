// File: ViewModels/WorkoutViewModel.swift
// F-003: Workout timer with background support
// Source: Apple Background Execution — https://developer.apple.com/documentation/uikit/app_and_environment/scenes/preparing_your_ui_to_run_in_the_background
// "beginBackgroundTask gives the app time to complete important tasks when moved to the background."

import Foundation
import SwiftData
import Observation
import UIKit

@Observable
@MainActor
final class WorkoutViewModel {
    var elapsedSeconds: Int = 0
    var zone2Seconds: Int = 0
    var isRunning: Bool = false

    /// Exposed internal for testability — stores timer start anchor
    private(set) var startDate: Date? = nil

    private var timer: Timer?
    private var backgroundTaskID: UIBackgroundTaskIdentifier = .invalid

    var formattedTime: String {
        let minutes = elapsedSeconds / 60
        let seconds = elapsedSeconds % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }

    func startTimer() {
        startDate = Date.now
        isRunning = true

        // Source: Apple docs — beginBackgroundTask keeps app alive briefly in background
        backgroundTaskID = UIApplication.shared.beginBackgroundTask(withName: "Zone2Timer") { [weak self] in
            self?.endBackgroundTask()
        }

        // Use .common RunLoop mode so timer fires during scroll gestures
        // MainActor.assumeIsolated: Timer fires on RunLoop.main, so main actor isolation is guaranteed
        let t = Timer(timeInterval: 1.0, repeats: true) { [weak self] _ in
            MainActor.assumeIsolated {
                guard let self, let startDate = self.startDate else { return }
                // Compute from startDate for background accuracy (elapsed is correct even after suspend)
                self.elapsedSeconds = max(0, Int(Date.now.timeIntervalSince(startDate)))
                self.zone2Seconds = self.elapsedSeconds
            }
        }
        RunLoop.main.add(t, forMode: .common)
        timer = t
    }

    func stopTimer() {
        timer?.invalidate()
        timer = nil
        isRunning = false
        startDate = nil
        endBackgroundTask()
    }

    private func endBackgroundTask() {
        guard backgroundTaskID != .invalid else { return }
        UIApplication.shared.endBackgroundTask(backgroundTaskID)
        backgroundTaskID = .invalid
    }

    func stopAndSave(modelContext: ModelContext, age: Int) {
        stopTimer()
        guard elapsedSeconds > 0 else { return }
        let session = WorkoutSession(
            durationSeconds: elapsedSeconds,
            zone2Seconds: zone2Seconds,
            targetHR: Zone2Calculator.zone2MaxHR(age: age)
        )
        modelContext.insert(session)
        try? modelContext.save()
        elapsedSeconds = 0
        zone2Seconds = 0
    }
}
