import Foundation

/// Local, aggregate-only features for an experimental behavior predictor.
/// The caller must supply independently verified research consent.
struct ManagerHistoryFeatures: Codable, Equatable {
    let closedCases: Int
    let observedResponses: Int
    let positiveResponses: Int

    static func build(
        cases: [ManagerBenchCase],
        personId: String,
        before decision: Date,
        hasResearchConsent: Bool
    ) -> ManagerHistoryFeatures? {
        guard hasResearchConsent, !personId.isEmpty else { return nil }
        let eligible = cases.filter { row in
            guard row.personId == personId,
                  row.decisionPointAt < decision,
                  row.outcomeWindowSec > 0,
                  row.hasValidAssignment,
                  let closed = row.observationWindowClosedAt else { return false }
            let end = row.decisionPointAt.addingTimeInterval(TimeInterval(row.outcomeWindowSec))
            return end <= closed && closed < decision
        }
        // Ambiguous duplicate assignments fail closed, rather than weighting a person twice.
        let groups = Dictionary(grouping: eligible, by: { $0.deliveryId })
        let unique = groups.values.compactMap { $0.count == 1 ? $0.first : nil }
        var observed = 0
        var positive = 0
        for row in unique {
            guard let outcome = row.response.responded else { continue }
            if outcome {
                guard let timestamp = row.response.respondedAt,
                      row.containsInObservationWindow(timestamp),
                      timestamp < decision else { continue }
                positive += 1
            } else {
                guard row.response.respondedAt == nil else { continue }
            }
            observed += 1
        }
        return .init(closedCases: unique.count, observedResponses: observed,
                     positiveResponses: positive)
    }
}
