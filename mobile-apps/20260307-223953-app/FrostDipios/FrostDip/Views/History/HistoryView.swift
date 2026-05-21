import SwiftUI
import SwiftData

struct HistoryView: View {
    @Query(sort: \PlungeSession.date, order: .reverse) private var sessions: [PlungeSession]
    @Environment(\.modelContext) private var modelContext
    @State private var showPaywall = false

    private let subscriptionService = SubscriptionService.shared

    private var visibleSessions: [PlungeSession] {
        if subscriptionService.isPremium {
            return sessions
        }
        let sevenDaysAgo = Calendar.current.date(byAdding: .day, value: -7, to: Date()) ?? Date()
        return sessions.filter { $0.date >= sevenDaysAgo }
    }

    var body: some View {
        NavigationStack {
            List {
                ForEach(visibleSessions, id: \.id) { session in
                    NavigationLink {
                        SessionDetailView(session: session)
                    } label: {
                        SessionCardView(session: session)
                    }
                    .accessibilityIdentifier(AccessibilityID.sessionCard)
                }
                .onDelete { indexSet in
                    for index in indexSet {
                        let session = visibleSessions[index]
                        modelContext.delete(session)
                    }
                }

                if !subscriptionService.isPremium && sessions.count > visibleSessions.count {
                    Section {
                        Button {
                            showPaywall = true
                        } label: {
                            HStack {
                                Image(systemName: "lock.fill")
                                    .foregroundStyle(Theme.Colors.accent)
                                Text("View older sessions")
                                Spacer()
                                Text("Upgrade")
                                    .foregroundStyle(Theme.Colors.accent)
                            }
                        }
                        .accessibilityIdentifier(AccessibilityID.historyUpgradeBanner)
                    }
                }
            }
            .navigationTitle("History")
            .sheet(isPresented: $showPaywall) {
                PaywallView(isOnboarding: false, onDismiss: {
                    showPaywall = false
                })
            }
        }
        .accessibilityIdentifier(AccessibilityID.historyView)
    }
}

// MARK: - Session Card

struct SessionCardView: View {
    let session: PlungeSession

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.xxs) {
            HStack {
                Image(systemName: session.isContrastSession ? "flame.fill" : "snowflake")
                    .foregroundStyle(session.isContrastSession ? Theme.Colors.hot : Theme.Colors.cold)

                Text(session.isContrastSession ? "Contrast" : "Cold Plunge")
                    .font(Theme.Typography.headline)

                Spacer()

                Text(formattedDuration)
                    .font(Theme.Typography.timerSmall)
                    .foregroundStyle(Theme.Colors.accent)
            }

            HStack(spacing: Theme.Spacing.sm) {
                if let temp = session.waterTemperature {
                    Label(String(format: "%.1f\u{00B0}C", temp), systemImage: "thermometer.medium")
                        .font(Theme.Typography.caption)
                        .foregroundStyle(Theme.Colors.secondaryLabel)
                }

                if let hr = session.heartRateAvg {
                    Label("\(Int(hr)) BPM", systemImage: "heart.fill")
                        .font(Theme.Typography.caption)
                        .foregroundStyle(Theme.Colors.secondaryLabel)
                }
            }
        }
        .padding(.vertical, Theme.Spacing.xxs)
    }

    private var formattedDuration: String {
        let minutes = Int(session.duration) / 60
        let seconds = Int(session.duration) % 60
        return "\(minutes):\(String(format: "%02d", seconds))"
    }
}

// MARK: - Session Detail

struct SessionDetailView: View {
    let session: PlungeSession

    var body: some View {
        List {
            Section("Session Info") {
                row("Date", value: session.date.formatted(date: .abbreviated, time: .shortened))
                row("Duration", value: formattedDuration)
                row("Protocol", value: session.protocolName ?? "Custom")
            }

            if session.waterTemperature != nil || session.heartRateAvg != nil {
                Section("Metrics") {
                    if let temp = session.waterTemperature {
                        row("Temperature", value: String(format: "%.1f\u{00B0}C", temp))
                    }
                    if let avgHR = session.heartRateAvg {
                        row("Avg Heart Rate", value: "\(Int(avgHR)) BPM")
                    }
                    if let maxHR = session.heartRateMax {
                        row("Max Heart Rate", value: "\(Int(maxHR)) BPM")
                    }
                }
            }

            if !session.notes.isEmpty {
                Section("Notes") {
                    Text(session.notes)
                        .font(Theme.Typography.body)
                }
            }
        }
        .navigationTitle("Session Detail")
        .navigationBarTitleDisplayMode(.inline)
        .accessibilityIdentifier(AccessibilityID.sessionDetailView)
    }

    private func row(_ label: String, value: String) -> some View {
        HStack {
            Text(label)
                .foregroundStyle(Theme.Colors.secondaryLabel)
            Spacer()
            Text(value)
                .font(Theme.Typography.headline)
        }
    }

    private var formattedDuration: String {
        let minutes = Int(session.duration) / 60
        let seconds = Int(session.duration) % 60
        return "\(minutes):\(String(format: "%02d", seconds))"
    }
}
