import SwiftUI
import SwiftData

struct HistoryView: View {
    @Query(sort: \Affirmation.createdAt, order: .reverse)
    private var affirmations: [Affirmation]

    var body: some View {
        Group {
            if affirmations.isEmpty {
                ContentUnavailableView(
                    "No History Yet",
                    systemImage: "clock.arrow.circlepath",
                    description: Text("Your affirmations will appear here")
                )
            } else {
                List {
                    ForEach(groupedByDate, id: \.key) { date, items in
                        Section(header: Text(date.formatted(date: .abbreviated, time: .omitted))) {
                            ForEach(items) { affirmation in
                                AffirmationRow(affirmation: affirmation)
                            }
                        }
                    }
                }
                .listStyle(.insetGrouped)
            }
        }
        .navigationTitle("History")
        .navigationBarTitleDisplayMode(.large)
    }

    private var groupedByDate: [(key: Date, value: [Affirmation])] {
        let grouped = Dictionary(grouping: affirmations) { affirmation in
            Calendar.current.startOfDay(for: affirmation.createdAt)
        }
        return grouped.sorted { $0.key > $1.key }
    }
}

#Preview {
    NavigationStack {
        HistoryView()
    }
}
