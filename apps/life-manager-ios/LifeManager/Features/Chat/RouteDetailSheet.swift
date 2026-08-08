import SwiftUI

struct RouteDetailSheet: View {
    let presentation: RouteDetailPresentation
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if let eventTitle = presentation.eventTitle {
                        Text(eventTitle)
                            .font(.title3.weight(.semibold))
                    }

                    Text("\(presentation.origin) → \(presentation.destination)")
                        .font(.headline)

                    ForEach(presentation.steps) { step in
                        VStack(alignment: .leading, spacing: 4) {
                            Text("\(time(step.departAt, timezone: presentation.timezone))  \(step.instruction)")
                                .font(.body.weight(.medium))
                            Text("\(step.from) → \(step.to)")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                            if let service = step.service {
                                Text(service)
                                    .font(.subheadline)
                            }
                            if let headsign = step.headsign {
                                Text(headsign)
                                    .font(.subheadline)
                            }
                            if let platform = step.platform {
                                Text(platform)
                                    .font(.subheadline)
                            }
                        }
                        .accessibilityElement(children: .combine)
                    }

                    HStack(spacing: 4) {
                        Text("route.arrive")
                        Text(time(presentation.arriveAt, timezone: presentation.timezone))
                        Text("·")
                        bufferLabel(presentation.bufferSeconds)
                    }
                    .font(.body.weight(.medium))

                    Text(presentation.providerAttribution)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
            }
            .navigationTitle("route.details")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("route.close") { dismiss() }
                        .accessibilityIdentifier("route.detail.close")
                }
            }
        }
    }

    private func time(_ date: Date, timezone: String) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .none
        formatter.timeStyle = .short
        formatter.timeZone = TimeZone(identifier: timezone) ?? .current
        return formatter.string(from: date)
    }

    private func bufferLabel(_ seconds: Int) -> some View {
        HStack(spacing: 4) {
            Text("\(max(0, seconds / 60))")
            Text("route.minutesEarly")
        }
    }
}
