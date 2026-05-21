import SwiftUI

struct ProgressDashboardView: View {
    @Environment(AppState.self) private var appState

    private let columns = [
        GridItem(.flexible(), spacing: 16),
        GridItem(.flexible(), spacing: 16)
    ]

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    StreakBadge(streak: appState.userProgress.streak)
                        .padding(.top, 16)

                    LazyVGrid(columns: columns, spacing: 16) {
                        StatCard(
                            title: String(localized: "Today"),
                            value: "\(appState.userProgress.todayCount)",
                            icon: "flame.fill",
                            color: .orange
                        )
                        StatCard(
                            title: String(localized: "Streak"),
                            value: "\(appState.userProgress.streak)",
                            icon: "bolt.fill",
                            color: .yellow
                        )
                        StatCard(
                            title: String(localized: "Total Sessions"),
                            value: "\(appState.userProgress.totalSessions)",
                            icon: "figure.flexibility",
                            color: .blue
                        )
                        StatCard(
                            title: String(localized: "Total Minutes"),
                            value: "\(appState.userProgress.totalMinutes)",
                            icon: "clock.fill",
                            color: .green
                        )
                    }
                    .padding(.horizontal)

                    WeekHistoryView(history: appState.userProgress.weekHistory)
                        .padding(.horizontal)
                }
            }
            .navigationTitle(String(localized: "Progress"))
        }
    }
}

struct StatCard: View {
    let title: String
    let value: String
    let icon: String
    let color: Color

    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(color)

            Text(value)
                .font(.title)
                .fontWeight(.bold)

            Text(title)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 20)
        .background(Color(.systemGray6))
        .cornerRadius(16)
    }
}

struct WeekHistoryView: View {
    let history: [String: Int]

    private let dayLabels = ["M", "T", "W", "T", "F", "S", "S"]

    var weekDates: [Date] {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        return (0..<7).compactMap { offset in
            calendar.date(byAdding: .day, value: -(6 - offset), to: today)
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(String(localized: "This Week"))
                .font(.headline)

            HStack(spacing: 0) {
                ForEach(Array(weekDates.enumerated()), id: \.offset) { index, date in
                    let key = ISO8601DateFormatter().string(from: date)
                    let count = history[key] ?? 0

                    VStack(spacing: 8) {
                        Circle()
                            .fill(count > 0 ? Color.accentColor : Color(.systemGray4))
                            .frame(width: 12, height: 12)

                        Text(dayLabels[index])
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                    .frame(maxWidth: .infinity)
                }
            }
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(16)
    }
}
