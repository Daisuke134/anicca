// File: Services/Zone2Calculator.swift
// Implements F-001: Maffetone Method (pure function — no AI, no external API)
// Source: Maffetone 180 Formula — https://philmaffetone.com/180-formula/
// "Maximum Aerobic Function HR = 180 - age."

import Foundation

enum Zone2Calculator {
    /// F-001: Maffetone Formula. Zone 2 upper bound.
    static func zone2MaxHR(age: Int) -> Int {
        180 - age
    }

    /// Zone 2 lower bound (±10 bpm range)
    static func zone2MinHR(age: Int) -> Int {
        zone2MaxHR(age: age) - 10
    }

    /// Full Zone 2 range as ClosedRange
    static func zone2Range(age: Int) -> ClosedRange<Int> {
        zone2MinHR(age: age)...zone2MaxHR(age: age)
    }
}
