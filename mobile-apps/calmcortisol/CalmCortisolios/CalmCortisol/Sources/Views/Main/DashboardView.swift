import SwiftUI

struct DashboardView: View {
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @State private var showSession = false
    @State private var showPaywall = false
    @State private var sessionCount = 0

    var body: some View {
        NavigationView {
            ZStack {
                Color(hex: "#0a1628").ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 20) {
                        Spacer().frame(height: 8)

                        // Cortisol bar
                        cortisolBarView
                            .accessibilityIdentifier("cortisol-bar")

                        // Daily mission
                        dailyMissionView
                            .accessibilityIdentifier("daily-mission-card")

                        // Quick start
                        Button {
                            if subscriptionManager.canStartSession {
                                showSession = true
                            } else {
                                showPaywall = true
                            }
                        } label: {
                            HStack {
                                Image(systemName: "lungs.fill")
                                    .font(.system(size: 20))
                                Text(L10n.dashboardStartCTA)
                                    .font(.system(size: 17, weight: .semibold))
                                Spacer()
                                Image(systemName: "chevron.right")
                                    .font(.system(size: 14))
                            }
                            .foregroundColor(.white)
                            .padding(20)
                            .background(Color(hex: "#2dd4bf"))
                            .cornerRadius(14)
                        }
                        .padding(.horizontal, 24)
                        .accessibilityIdentifier("quick-start-cta")

                        // Session history
                        sessionHistoryView
                            .accessibilityIdentifier("session-history-card")

                        Spacer()
                    }
                }
            }
            .navigationTitle("CalmCortisol")
            .navigationBarTitleDisplayMode(.large)
            .sheet(isPresented: $showSession) {
                SessionView()
                    .environmentObject(subscriptionManager)
            }
            .sheet(isPresented: $showPaywall) {
                PaywallView(isOnboarding: false)
                    .environmentObject(subscriptionManager)
            }
        }
        .onAppear {
            sessionCount = SessionStore.shared.todayCount()
        }
    }

    private var cortisolBarView: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(L10n.dashboardTitle)
                .font(.system(size: 15, weight: .medium))
                .foregroundColor(Color(hex: "#9ca3af"))

            let level = cortisolLevel()
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 6)
                        .fill(Color(hex: "#1f2937"))
                        .frame(height: 12)

                    RoundedRectangle(cornerRadius: 6)
                        .fill(cortisolColor(level))
                        .frame(width: geo.size.width * CGFloat(level), height: 12)
                }
            }
            .frame(height: 12)

            Text(cortisolLabel(level))
                .font(.system(size: 13))
                .foregroundColor(cortisolColor(level))
        }
        .padding(20)
        .background(Color(hex: "#111827"))
        .cornerRadius(14)
        .padding(.horizontal, 24)
    }

    private var dailyMissionView: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(L10n.dashboardMission)
                    .font(.system(size: 15, weight: .medium))
                    .foregroundColor(.white)
                Text("\(min(sessionCount, 3))/3 \(L10n.isJapaneseLang ? "完了" : "completed")")
                    .font(.system(size: 13))
                    .foregroundColor(Color(hex: "#9ca3af"))
            }
            Spacer()
            ZStack {
                Circle()
                    .stroke(Color(hex: "#1f2937"), lineWidth: 4)
                    .frame(width: 48, height: 48)
                Circle()
                    .trim(from: 0, to: CGFloat(min(sessionCount, 3)) / 3)
                    .stroke(Color(hex: "#2dd4bf"), style: StrokeStyle(lineWidth: 4, lineCap: .round))
                    .frame(width: 48, height: 48)
                    .rotationEffect(.degrees(-90))
                Text("\(min(sessionCount, 3))")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundColor(.white)
            }
        }
        .padding(20)
        .background(Color(hex: "#111827"))
        .cornerRadius(14)
        .padding(.horizontal, 24)
    }

    private var sessionHistoryView: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(L10n.dashboardSessionCount)
                    .font(.system(size: 15, weight: .medium))
                    .foregroundColor(.white)
                Text("\(sessionCount) \(L10n.isJapaneseLang ? "セッション" : "sessions")")
                    .font(.system(size: 28, weight: .bold))
                    .foregroundColor(Color(hex: "#2dd4bf"))
            }
            Spacer()
            Image(systemName: "chart.bar.fill")
                .font(.system(size: 28))
                .foregroundColor(Color(hex: "#1f2937"))
        }
        .padding(20)
        .background(Color(hex: "#111827"))
        .cornerRadius(14)
        .padding(.horizontal, 24)
    }

    private func cortisolLevel() -> Double {
        let hour = Calendar.current.component(.hour, from: Date())
        // Simulated cortisol pattern: peaks at 8-9am, low at night
        switch hour {
        case 7...9: return 0.8
        case 10...12: return 0.6
        case 13...15: return 0.5
        case 16...18: return 0.65
        case 19...21: return 0.4
        default: return 0.3
        }
    }

    private func cortisolColor(_ level: Double) -> Color {
        if level > 0.7 { return Color(hex: "#ef4444") }
        if level > 0.5 { return Color(hex: "#f59e0b") }
        return Color(hex: "#2dd4bf")
    }

    private func cortisolLabel(_ level: Double) -> String {
        if level > 0.7 { return L10n.isJapaneseLang ? "高め - 呼吸セッションを推奨" : "High - Breathing session recommended" }
        if level > 0.5 { return L10n.isJapaneseLang ? "やや高め" : "Slightly elevated" }
        return L10n.isJapaneseLang ? "良好" : "Good"
    }
}
