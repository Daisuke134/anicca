import SwiftUI

struct StreakBadge: View {
    let streak: Int

    var body: some View {
        HStack(spacing: 4) {
            if streak > 0 {
                Text("🔥")
                Text("\(streak)")
                    .font(.headline)
                    .fontWeight(.bold)
                Text(String(localized: "day streak"))
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(streak > 0 ? Color.orange.opacity(0.12) : Color.clear)
        .cornerRadius(20)
    }
}
