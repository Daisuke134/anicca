import SwiftUI
import SwiftData

struct HistoryView: View {
    @Query(sort: \CheckIn.date, order: .reverse) private var checkIns: [CheckIn]

    var body: some View {
        NavigationStack {
            Group {
                if checkIns.isEmpty {
                    emptyState
                } else {
                    List(checkIns) { checkIn in
                        NavigationLink {
                            ResultView(checkIn: checkIn)
                                .navigationTitle(checkIn.date.formatted(.dateTime.month().day()))
                        } label: {
                            HistoryRow(checkIn: checkIn)
                        }
                    }
                }
            }
            .navigationTitle(NSLocalizedString("History", comment: ""))
        }
    }

    private var emptyState: some View {
        VStack(spacing: Spacing.md) {
            Image(systemName: "calendar.badge.plus")
                .font(.system(size: 48))
                .foregroundStyle(Color.secondary)
            Text(NSLocalizedString("Complete your first check-in to see history", comment: ""))
                .font(.headline)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
        }
        .padding(Spacing.xl)
    }
}

struct HistoryRow: View {
    let checkIn: CheckIn
    private var constitution: ConstitutionType { ConstitutionType.from(string: checkIn.constitutionType) }

    var body: some View {
        HStack {
            Image(systemName: constitution.icon)
                .foregroundStyle(constitution.color)
            VStack(alignment: .leading) {
                Text(checkIn.date.formatted(.dateTime.weekday(.wide).month().day()))
                    .font(.headline)
                Text(constitution.rawValue)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, Spacing.xs)
    }
}
