// File: DesignSystem/Colors.swift
// Brand color tokens — DESIGN_SYSTEM.md §1
// Source: docs/DESIGN_SYSTEM.md — "Token names: camelCase, exact match"

import SwiftUI

extension Color {
    // Primary brand (CTA, active states)
    static let brandPrimary = Color("brandPrimary")
    // Semantic
    static let brandSuccess = Color("brandSuccess")
    static let brandWarning = Color("brandWarning")
    static let brandDanger = Color("brandDanger")
    // Background
    static let bgPrimary = Color("bgPrimary")
    static let bgSecondary = Color("bgSecondary")
    // Surface
    static let surfaceCard = Color("surfaceCard")
    // Text
    static let textPrimary = Color("textPrimary")
    static let textSecondary = Color("textSecondary")
}

extension ShapeStyle where Self == Color {
    static var brandPrimary: Color { .brandPrimary }
    static var brandSuccess: Color { .brandSuccess }
    static var brandWarning: Color { .brandWarning }
    static var brandDanger: Color { .brandDanger }
    static var bgPrimary: Color { .bgPrimary }
    static var bgSecondary: Color { .bgSecondary }
    static var surfaceCard: Color { .surfaceCard }
    static var textPrimary: Color { .textPrimary }
    static var textSecondary: Color { .textSecondary }
}
