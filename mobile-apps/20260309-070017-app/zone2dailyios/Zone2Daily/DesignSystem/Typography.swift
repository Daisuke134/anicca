// File: DesignSystem/Typography.swift
// Font scale — DESIGN_SYSTEM.md §2

import SwiftUI

extension Font {
    static let displayLarge: Font = .system(.largeTitle, design: .rounded, weight: .bold)
    static let displayMedium: Font = .system(.title, design: .rounded, weight: .bold)
    static let headlineMedium: Font = .system(.headline, design: .default, weight: .semibold)
    static let bodyRegular: Font = .system(.body, design: .default, weight: .regular)
    static let labelSmall: Font = .system(.caption, design: .default, weight: .regular)
}
