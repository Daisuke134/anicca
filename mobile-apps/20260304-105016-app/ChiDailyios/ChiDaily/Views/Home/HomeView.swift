import SwiftUI
import SwiftData

struct HomeView: View {
    @Query(sort: \CheckIn.date, order: .reverse) private var checkIns: [CheckIn]
    @Environment(SubscriptionService.self) private var subscriptionService
    @State private var showCheckIn = false
    @State private var showPaywall = false

    private var todayCheckIn: CheckIn? {
        checkIns.first { Calendar.current.isDateInToday($0.date) }
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: Spacing.lg) {
                    greetingSection
                    if let checkIn = todayCheckIn {
                        ResultSummaryCard(checkIn: checkIn)
                    } else {
                        startCheckInCard
                    }
                }
                .padding(Spacing.md)
            }
            .navigationTitle("Chi Daily")
            .navigationBarTitleDisplayMode(.inline)
        }
        .sheet(isPresented: $showCheckIn) {
            CheckInView()
        }
        .sheet(isPresented: $showPaywall) {
            PaywallView()
                .environment(subscriptionService)
        }
    }

    private var greetingSection: some View {
        VStack(alignment: .leading) {
            Text(Date().formatted(.dateTime.weekday(.wide).month().day()))
                .font(.headline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var startCheckInCard: some View {
        VStack(spacing: Spacing.md) {
            Text(NSLocalizedString("How are you feeling today?", comment: ""))
                .font(.title2).bold()
            PrimaryButton(title: NSLocalizedString("Start Today's Check-in", comment: "")) {
                if subscriptionService.canStartCheckIn() {
                    showCheckIn = true
                } else {
                    showPaywall = true
                }
            }
        }
        .padding(Spacing.md)
        .background(Color.chiSurface)
        .cornerRadius(16)
    }
}
