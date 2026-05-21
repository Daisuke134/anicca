// File: Models/WorkoutSession.swift
// Implements F-003: WorkoutSession data model
// Source: Apple SwiftData WWDC 2023 — https://developer.apple.com/videos/play/wwdc2023/10187/
// "SwiftData is the modern replacement for CoreData on iOS 17+."

import SwiftData
import Foundation

@Model
final class WorkoutSession {
    var id: UUID
    var date: Date
    var durationSeconds: Int
    var zone2Seconds: Int
    var targetHR: Int
    var notes: String?

    init(date: Date = .now, durationSeconds: Int, zone2Seconds: Int, targetHR: Int, notes: String? = nil) {
        self.id = UUID()
        self.date = date
        self.durationSeconds = durationSeconds
        self.zone2Seconds = zone2Seconds
        self.targetHR = targetHR
        self.notes = notes
    }

    var zone2Minutes: Double { Double(zone2Seconds) / 60.0 }

    var zone2Percentage: Double {
        guard durationSeconds > 0 else { return 0 }
        return Double(zone2Seconds) / Double(durationSeconds) * 100.0
    }
}
