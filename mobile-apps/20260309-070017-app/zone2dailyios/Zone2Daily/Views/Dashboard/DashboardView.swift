// File: Views/Dashboard/DashboardView.swift
// SCR-005: Weekly Zone 2 progress dashboard
// F-004: Weekly progress + streak + 7-day activity chart

import SwiftUI
import SwiftData

struct DashboardView: View {
    @Query private var sessions: [WorkoutSession]
    @Query private var profiles: [UserProfile]
    @Environment(SubscriptionService.self) private var subscriptionService
    @State private var viewModel = DashboardViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    if let profile = profiles.first {
                        hrTargetSection(profile: profile)
                    }
                    weeklyGoalSection
                    WeeklyProgressView(
                        activities: viewModel.weekdayActivity,
                        goalMinutes: viewModel.weeklyGoalMinutes
                    )
                    recentSessionsSection
                }
                .padding()
            }
            .navigationTitle("Dashboard")
            .onAppear { viewModel.loadWeeklyData(sessions: sessions) }
            .onChange(of: sessions.count) { viewModel.loadWeeklyData(sessions: sessions) }
        }
        .accessibilityIdentifier("screen_dashboard")
    }

    private func hrTargetSection(profile: UserProfile) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text("Zone 2 Target HR")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text("\(Zone2Calculator.zone2MinHR(age: profile.age))–\(Zone2Calculator.zone2MaxHR(age: profile.age)) bpm")
                    .font(.title2.bold())
                    .foregroundStyle(.brandPrimary)
                    .accessibilityIdentifier("label_zone2_target")
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                Text("Streak")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text("\(viewModel.streak) 🔥")
                    .font(.title2.bold())
                    .accessibilityIdentifier("label_streak")
            }
        }
        .padding()
        .background(.surfaceCard)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var weeklyGoalSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("\(Int(viewModel.weeklyZone2Minutes)) min")
                    .font(.title2.bold())
                    .accessibilityIdentifier("label_weekly_progress")
                Spacer()
                Text("/ \(viewModel.weeklyGoalMinutes) min goal")
                    .foregroundStyle(.secondary)
            }
            ProgressView(value: viewModel.progressFraction)
                .tint(.brandPrimary)
                .accessibilityIdentifier("ring_weekly_progress")
        }
        .padding()
        .background(.surfaceCard)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var recentSessionsSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Recent Sessions")
                .font(.headline)
            let sorted = sessions.sorted { $0.date > $1.date }
            let limit = subscriptionService.isPremium ? 10 : 3
            ForEach(sorted.prefix(limit)) { session in
                SessionRowView(session: session)
            }
            if !subscriptionService.isPremium && sessions.count > 3 {
                Text("Upgrade to see all sessions")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

struct SessionRowView: View {
    let session: WorkoutSession

    var body: some View {
        HStack {
            VStack(alignment: .leading) {
                Text(session.date, style: .date)
                    .font(.subheadline)
                Text("\(Int(session.zone2Minutes)) min Zone 2")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Text(String(format: "%.0f%%", session.zone2Percentage))
                .font(.subheadline.bold())
                .foregroundStyle(session.zone2Percentage > 60 ? .brandSuccess : .brandWarning)
        }
        .padding(.vertical, 4)
    }
}
