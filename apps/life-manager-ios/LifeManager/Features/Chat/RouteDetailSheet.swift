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

                    VStack(alignment: .leading, spacing: 4) {
                        HStack(spacing: 4) {
                            Text("route.leave")
                            Text(time(presentation.leaveAt, timezone: presentation.timezone))
                        }
                        HStack(spacing: 4) {
                            Text("route.arrive")
                            Text(time(presentation.arriveAt, timezone: presentation.timezone))
                        }
                    }

                    ForEach(presentation.steps) { step in
                        VStack(alignment: .leading, spacing: 4) {
                            if let instruction = step.instruction, let departAt = step.departAt {
                                Text("\(time(departAt, timezone: presentation.timezone))  \(instruction)")
                                    .font(.body.weight(.medium))
                            } else if let instruction = step.instruction {
                                Text(instruction)
                                    .font(.body.weight(.medium))
                            } else if let departAt = step.departAt {
                                Text(time(departAt, timezone: presentation.timezone))
                                    .font(.body.weight(.medium))
                            }
                            if let from = step.from, let to = step.to {
                                Text("\(from) → \(to)")
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            } else if let from = step.from {
                                Text(from)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            } else if let to = step.to {
                                Text(to)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
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

                    if let bufferSeconds = presentation.bufferSeconds {
                        HStack(spacing: 4) {
                            Text("route.bufferReason")
                            bufferLabel(bufferSeconds)
                        }
                        .font(.body.weight(.medium))
                    }

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

                    VStack(alignment: .leading, spacing: 4) {
                        Text("route.liveLocationOff")
                        Text("route.unsupportedFieldsOmitted")
                    }
                    .font(.footnote)
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
