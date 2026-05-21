import SwiftUI

struct ResultView: View {
    let checkIn: CheckIn
    let onDone: (() -> Void)?
    private let constitution: ConstitutionType

    init(checkIn: CheckIn, onDone: (() -> Void)? = nil) {
        self.checkIn = checkIn
        self.onDone = onDone
        self.constitution = ConstitutionType.from(string: checkIn.constitutionType)
    }

    var body: some View {
        ScrollView {
            VStack(spacing: Spacing.xl) {
                ConstitutionBadge(type: constitution)
                    .padding(.top, Spacing.xl)

                Divider()

                VStack(spacing: Spacing.md) {
                    RecommendationCard(
                        category: .food,
                        title: NSLocalizedString("Food", comment: ""),
                        bodyText: checkIn.foodRecommendation
                    )
                    RecommendationCard(
                        category: .movement,
                        title: NSLocalizedString("Movement", comment: ""),
                        bodyText: checkIn.movementRecommendation
                    )
                    RecommendationCard(
                        category: .rest,
                        title: NSLocalizedString("Rest", comment: ""),
                        bodyText: checkIn.restRecommendation
                    )
                }
                .padding(.horizontal, Spacing.md)

                if let onDone = onDone {
                    PrimaryButton(title: NSLocalizedString("Done ✓", comment: "")) { onDone() }
                        .padding(.horizontal, Spacing.md)
                        .padding(.bottom, Spacing.xl)
                }
            }
        }
    }
}
