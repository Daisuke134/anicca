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
                        .accessibilityLabel(Text(eventTitle))
                }

                Text("\(presentation.origin) → \(presentation.destination)")
                    .font(.subheadline.weight(.semibold))
                    .accessibilityLabel(Text("\(presentation.origin) → \(presentation.destination)"))

                HStack(alignment: .top, spacing: 16) {
                    timingLabel("route.leave", presentation.leaveAt, timezone: presentation.timezone, systemImage: "figure.walk")
                    timingLabel("route.arrive", presentation.arriveAt, timezone: presentation.timezone, systemImage: "flag")
                }
                .font(.subheadline)

                HStack(spacing: 16) {
                    durationLabel(presentation.durationSeconds)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("route.bufferReason")
                            .font(.caption)
                        bufferLabel(presentation.bufferSeconds)
                    }
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

                Button("route.showFull", action: onShowDetails)
                    .buttonStyle(.borderedProminent)
                    .accessibilityIdentifier("route.showDetails")

                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 4) {
                        Text("route.source")
                        Text(presentation.providerAttribution)
                    }
                    HStack(spacing: 4) {
                        Text("route.updated")
                        Text(time(presentation.computedAt, timezone: presentation.timezone))
                    }
                    if presentation.isUnofficialSource {
                        Text("route.unofficialWarning")
                    }
                }
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

    private func timingLabel(_ label: LocalizedStringKey, _ date: Date, timezone: String, systemImage: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Label(label, systemImage: systemImage)
                .font(.caption)
            Text(time(date, timezone: timezone))
        }
    }

    private func durationLabel(_ seconds: Int) -> some View {
        let minutes = max(0, seconds / 60)
        return HStack(spacing: 4) {
            Text("\(minutes)")
            Text("route.minutes")
        }
    }

    private func bufferLabel(_ seconds: Int) -> some View {
        let minutes = max(0, seconds / 60)
        return HStack(spacing: 4) {
            Text("\(minutes)")
            Text("route.minutesBuffer")
        }
    }

    private func fareText(_ fare: RouteFare) -> String {
        "\(fare.currency) \(fare.amount.formatted(.number.precision(.fractionLength(0)))) · \(fare.medium)"
    }
}
