import SwiftUI

struct PrimaryButton: View {
    let title: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .fontWeight(.semibold)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 16)
                .background(Color.chiAccent)
                .foregroundStyle(.white)
                .cornerRadius(14)
        }
    }
}

struct SecondaryOutlineButton: View {
    let title: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .fontWeight(.medium)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .overlay(
                    RoundedRectangle(cornerRadius: 14)
                        .stroke(Color.chiAccent, lineWidth: 1.5)
                )
                .foregroundStyle(Color.chiAccent)
        }
    }
}

struct FeatureRow: View {
    let icon: String
    let text: String

    var body: some View {
        HStack(spacing: Spacing.sm) {
            Image(systemName: icon)
                .foregroundStyle(Color.chiAccent)
            Text(text)
                .font(.body)
        }
    }
}

struct QuestionRow: View {
    let option: Int
    let label: String
    let emoji: String
    let isSelected: Bool
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: Spacing.md) {
                Text(emoji)
                    .font(.title2)
                Text(label)
                    .font(.body)
                    .foregroundStyle(isSelected ? .white : .primary)
                Spacer()
                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(.white)
                }
            }
            .padding(.horizontal, Spacing.md)
            .padding(.vertical, Spacing.sm)
            .background(isSelected ? Color.chiAccent : Color(.systemBackground))
            .cornerRadius(12)
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(isSelected ? Color.chiAccent : Color(.systemGray4), lineWidth: 1)
            )
        }
    }
}

struct ConstitutionBadge: View {
    let type: ConstitutionType

    var body: some View {
        VStack(spacing: Spacing.sm) {
            Image(systemName: type.icon)
                .font(.system(size: 48))
                .foregroundStyle(type.color)
            Text(type.rawValue)
                .font(.title).bold()
                .foregroundStyle(type.color)
            Text(type.japaneseName)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }
}

struct RecommendationCard: View {
    let category: RecommendationCategory
    let title: String
    let bodyText: String

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            HStack {
                Image(systemName: category.sfSymbol)
                    .foregroundStyle(category.color)
                Text(title)
                    .font(.headline)
                    .foregroundStyle(category.color)
            }
            Text(bodyText)
                .font(.body)
                .foregroundStyle(.primary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(Spacing.md)
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 4, x: 0, y: 2)
    }
}

struct ResultSummaryCard: View {
    let checkIn: CheckIn
    private var constitution: ConstitutionType { ConstitutionType.from(string: checkIn.constitutionType) }

    var body: some View {
        VStack(spacing: Spacing.md) {
            HStack {
                Image(systemName: constitution.icon)
                    .foregroundStyle(constitution.color)
                Text(constitution.rawValue)
                    .font(.headline)
                    .foregroundStyle(constitution.color)
                Spacer()
                Text(checkIn.date.formatted(.dateTime.hour().minute()))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Text(checkIn.foodRecommendation)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .lineLimit(2)
        }
        .padding(Spacing.md)
        .background(Color.chiSurface)
        .cornerRadius(16)
    }
}
