import SwiftUI
import SwiftData
import Charts

struct ProgressDashboardView: View {
    @State private var viewModel = ProgressViewModel()
    @Query(sort: \PlungeSession.date, order: .reverse) private var sessions: [PlungeSession]
    @State private var showPaywall = false

    private let subscriptionService = SubscriptionService.shared

    var body: some View {
        NavigationStack {
            Group {
                if subscriptionService.isPremium {
                    premiumContent
                } else {
                    freeContent
                }
            }
            .navigationTitle("Progress")
            .sheet(isPresented: $showPaywall) {
                PaywallView(isOnboarding: false, onDismiss: {
                    showPaywall = false
                })
            }
            .onAppear {
                viewModel.updateSessions(sessions)
                viewModel.refreshStreaks()
            }
            .onChange(of: sessions.count) { _, _ in
                viewModel.updateSessions(sessions)
            }
        }
        .accessibilityIdentifier(AccessibilityID.progressView)
    }

    // MARK: - Premium Content

    private var premiumContent: some View {
        ScrollView {
            VStack(spacing: Theme.Spacing.lg) {
                streakSection
                calendarSection
                chartSection
                statsSection
            }
            .padding(Theme.Spacing.md)
        }
    }

    // MARK: - Free Content (Blurred Preview)

    private var freeContent: some View {
        ZStack {
            premiumContent
                .blur(radius: 8)
                .allowsHitTesting(false)

            VStack(spacing: Theme.Spacing.md) {
                Image(systemName: "lock.fill")
                    .font(.system(size: 40))
                    .foregroundStyle(Theme.Colors.accent)

                Text("Unlock Progress")
                    .font(Theme.Typography.title2)

                Text("Track your cold plunge journey")
                    .font(Theme.Typography.subheadline)
                    .foregroundStyle(Theme.Colors.secondaryLabel)

                Button {
                    showPaywall = true
                } label: {
                    Text("Upgrade to Premium")
                        .font(Theme.Typography.headline)
                        .frame(maxWidth: .infinity, minHeight: 50)
                }
                .buttonStyle(.borderedProminent)
                .tint(Theme.Colors.accent)
                .padding(.horizontal, Theme.Spacing.xxl)
            }
        }
    }

    // MARK: - Streaks

    private var streakSection: some View {
        HStack(spacing: Theme.Spacing.lg) {
            VStack(spacing: Theme.Spacing.xxs) {
                Text("\(viewModel.currentStreak)")
                    .font(Theme.Typography.largeTitle)
                    .foregroundStyle(Theme.Colors.hot)
                    .accessibilityIdentifier(AccessibilityID.streakCurrent)
                Text("Current Streak")
                    .font(Theme.Typography.caption)
                    .foregroundStyle(Theme.Colors.secondaryLabel)
            }

            Spacer()

            VStack(spacing: Theme.Spacing.xxs) {
                Text("\(viewModel.longestStreak)")
                    .font(Theme.Typography.largeTitle)
                    .foregroundStyle(Theme.Colors.accent)
                    .accessibilityIdentifier(AccessibilityID.streakLongest)
                Text("Best Streak")
                    .font(Theme.Typography.caption)
                    .foregroundStyle(Theme.Colors.secondaryLabel)
            }
        }
        .padding(Theme.Spacing.md)
        .background(Theme.Colors.secondaryBackground)
        .clipShape(RoundedRectangle(cornerRadius: Theme.CornerRadius.large))
    }

    // MARK: - Calendar

    private var calendarSection: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
            Text("Last 30 Days")
                .font(Theme.Typography.headline)

            LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 7), spacing: Theme.Spacing.xxs) {
                ForEach(viewModel.weekdayLabels, id: \.self) { label in
                    Text(label)
                        .font(Theme.Typography.caption)
                        .foregroundStyle(Theme.Colors.secondaryLabel)
                }

                ForEach(last30Days, id: \.self) { date in
                    let hasSession = sessions.contains { Calendar.current.isDate($0.date, inSameDayAs: date) }
                    Circle()
                        .fill(hasSession ? Theme.Colors.accent : Theme.Colors.cold.opacity(0.2))
                        .frame(width: 28, height: 28)
                }
            }
        }
        .padding(Theme.Spacing.md)
        .background(Theme.Colors.secondaryBackground)
        .clipShape(RoundedRectangle(cornerRadius: Theme.CornerRadius.large))
        .accessibilityIdentifier(AccessibilityID.streakCalendar)
    }

    private var last30Days: [Date] {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        return (0..<30).compactMap { calendar.date(byAdding: .day, value: -$0, to: today) }.reversed()
    }

    // MARK: - Chart

    private var chartSection: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
            Text("Duration Trend")
                .font(Theme.Typography.headline)

            if sessions.isEmpty {
                Text("Complete sessions to see trends")
                    .font(Theme.Typography.subheadline)
                    .foregroundStyle(Theme.Colors.secondaryLabel)
                    .frame(height: 150)
                    .frame(maxWidth: .infinity)
            } else {
                Chart(sessions.prefix(30).reversed(), id: \.id) { session in
                    LineMark(
                        x: .value("Date", session.date, unit: .day),
                        y: .value("Duration", session.duration / 60)
                    )
                    .foregroundStyle(Theme.Colors.accent)

                    PointMark(
                        x: .value("Date", session.date, unit: .day),
                        y: .value("Duration", session.duration / 60)
                    )
                    .foregroundStyle(Theme.Colors.accent)
                }
                .chartYAxisLabel("Minutes")
                .frame(height: 150)
            }
        }
        .padding(Theme.Spacing.md)
        .background(Theme.Colors.secondaryBackground)
        .clipShape(RoundedRectangle(cornerRadius: Theme.CornerRadius.large))
        .accessibilityIdentifier(AccessibilityID.progressDurationChart)
    }

    // MARK: - Stats

    private var statsSection: some View {
        HStack(spacing: Theme.Spacing.sm) {
            statCard(value: "\(viewModel.totalSessions)", label: "Total\nSessions")
            statCard(value: viewModel.formattedDuration(viewModel.averageDuration), label: "Avg\nDuration")
            statCard(
                value: viewModel.averageTemperature.map { String(format: "%.1f\u{00B0}", $0) } ?? "--",
                label: "Avg\nTemp"
            )
        }
    }

    private func statCard(value: String, label: String) -> some View {
        VStack(spacing: Theme.Spacing.xxs) {
            Text(value)
                .font(Theme.Typography.title2)
                .foregroundStyle(Theme.Colors.accent)
            Text(label)
                .font(Theme.Typography.caption)
                .foregroundStyle(Theme.Colors.secondaryLabel)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(Theme.Spacing.sm)
        .background(Theme.Colors.secondaryBackground)
        .clipShape(RoundedRectangle(cornerRadius: Theme.CornerRadius.medium))
    }
}
