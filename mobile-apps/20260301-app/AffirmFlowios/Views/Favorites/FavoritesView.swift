import SwiftUI
import SwiftData

struct FavoritesView: View {
    @Query(filter: #Predicate<Affirmation> { $0.isFavorite },
           sort: \Affirmation.createdAt,
           order: .reverse)
    private var favorites: [Affirmation]

    var body: some View {
        Group {
            if favorites.isEmpty {
                ContentUnavailableView(
                    "No Favorites Yet",
                    systemImage: "star",
                    description: Text("Tap the heart on affirmations you love")
                )
            } else {
                List {
                    ForEach(favorites) { affirmation in
                        AffirmationRow(affirmation: affirmation)
                    }
                }
                .listStyle(.plain)
            }
        }
        .navigationTitle("Favorites")
        .navigationBarTitleDisplayMode(.large)
    }
}

struct AffirmationRow: View {
    let affirmation: Affirmation

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            Text(affirmation.content)
                .font(.body)

            HStack {
                Image(systemName: affirmation.focusArea.systemImage)
                    .foregroundColor(affirmation.focusArea.color)
                    .font(.caption)
                Text(affirmation.focusArea.rawValue)
                    .font(.caption)
                    .foregroundColor(.secondary)

                Spacer()

                Text(affirmation.createdAt.formatted(date: .abbreviated, time: .omitted))
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
            }
        }
        .padding(.vertical, Spacing.xs)
    }
}

#Preview {
    NavigationStack {
        FavoritesView()
    }
}
