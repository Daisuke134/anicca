// File: Models/UserProfile.swift
// Implements user profile data model with Maffetone HR calculation
// Source: Maffetone 180 Formula — https://philmaffetone.com/180-formula/
// "Maximum Aerobic Function HR = 180 - age."

import SwiftData
import Foundation

@Model
final class UserProfile {
    var age: Int
    var weeklyGoalMinutes: Int
    var createdAt: Date

    init(age: Int, weeklyGoalMinutes: Int = 150) {
        self.age = age
        self.weeklyGoalMinutes = weeklyGoalMinutes
        self.createdAt = .now
    }

    // F-001: Maffetone Formula
    var zone2MaxHR: Int { 180 - age }
    var zone2MinHR: Int { zone2MaxHR - 10 }
}
