// File: Views/Dashboard/WeeklyProgressView.swift
// SCR-006: 7-day Zone 2 activity bar chart
// F-004: Weekly progress visualization

import SwiftUI

struct WeeklyProgressView: View {
    let activities: [WeekdayActivity]
    let goalMinutes: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("This Week")
                .font(.headline)
                .accessibilityIdentifier("dashboard_weekly_goal_label")

            HStack(alignment: .bottom, spacing: 6) {
                ForEach(Array(activities.enumerated()), id: \.offset) { _, activity in
                    barColumn(activity: activity)
                }
            }
            .frame(height: 60)
            .accessibilityIdentifier("dashboard_weekly_bars")
        }
        .padding()
        .background(.surfaceCard)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private func barColumn(activity: WeekdayActivity) -> some View {
        let fraction = goalMinutes > 0
            ? min(activity.minutes / Double(goalMinutes) * 7.0, 1.0)
            : 0.0

        return VStack(spacing: 4) {
            Spacer(minLength: 0)
            RoundedRectangle(cornerRadius: 3)
                .fill(activity.hasActivity ? Color.brandPrimary : Color.brandPrimary.opacity(0.2))
                .frame(height: max(4, fraction * 48))
            Text(activity.label)
                .font(.system(size: 9))
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
    }
}
