import SwiftUI

struct PainAreaCard: View {
    let painArea: PainArea
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 12) {
                Image(systemName: painArea.sfSymbol)
                    .font(.system(size: 32))
                    .foregroundColor(isSelected ? .white : .accentColor)

                Text(painArea.displayName)
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundColor(isSelected ? .white : .primary)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 20)
            .background(isSelected ? Color.accentColor : Color(.systemGray6))
            .cornerRadius(16)
        }
        .accessibilityIdentifier("pain_area_\(painArea.rawValue)")
    }
}
