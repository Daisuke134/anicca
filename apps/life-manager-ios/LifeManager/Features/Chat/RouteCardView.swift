import SwiftUI

struct RouteCardView: View {
    let message: ChatMessage
    let onShowDetails: () -> Void

    var body: some View {
        if let presentation = RoutePresentation.card(for: message) {
            VStack(alignment: .leading, spacing: 12) {
                if let eventTitle = presentation.eventTitle {
                    Text(eventTitle)
                        .font(.headline)
                        .accessibilityLabel("Event (eventTitle)")
                }

                Text("\(presentation.origin) → \(presentation.destination)")
                    .font(.subheadline.weight(.semibold))
                    .accessibilityLabel("From \(presentation.origin) to \(presentation.destination)")

                HStack(spacing: 16) {
                    Label(time(presentation.leaveAt, timezone: presentation.timezone), systemImage: "figure.walk")
                    Label(time(presentation.arriveAt, timezone: presentation.timezone), systemImage: "flag")
                }
                .font(.subheadline)

                HStack(spacing: 16) {
                    Text(duration(presentation.durationSeconds))
                    Text(buffer(presentation.bufferSeconds))
                }
                .font(.subheadline)

                if let fare = presentation.fare {
                    Text(fareText(fare))
                        .font(.subheadline)
                }

                if !presentation.legSummary.isEmpty {
                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(Array(presentation.legSummary.enumerated()), id: \.offset) { _, leg in
                            Text(leg)
                                .font(.body)
                        }
                    }
                }

                Button("Show full route", action: onShowDetails)
                    .buttonStyle(.borderedProminent)
                    .accessibilityIdentifier("route.showDetails")

                Text(presentation.providerAttribution)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding()
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 16))
            .accessibilityElement(children: .contain)
            .accessibilityIdentifier("route.card.\(message.id)")
        }
    }

    private func time(_ date: Date, timezone: String) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .none
        formatter.timeStyle = .short
        formatter.timeZone = TimeZone(identifier: timezone) ?? .current
        return formatter.string(from: date)
    }

    private func duration(_ seconds: Int) -> String {
        let minutes = max(0, seconds / 60)
        return "\(minutes) min"
    }

    private func buffer(_ seconds: Int) -> String {
        let minutes = max(0, seconds / 60)
        return "\(minutes) min buffer"
    }

    private func fareText(_ fare: RouteFare) -> String {
        "\(fare.currency) \(fare.amount.formatted(.number.precision(.fractionLength(0)))) · \(fare.medium)"
    }
}
