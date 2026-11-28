import Foundation
let now = Date(timeIntervalSince1970: 1_700_000_000)
func fixture(_ id: String, _ person: String = "p") -> ManagerBenchCase {
    var row = ManagerBenchCase(personId: person, deliveryId: id,
        decisionPointAt: now.addingTimeInterval(-100), source: "onboarding_first_intervention",
        outcomeWindowSec: 50,
        situation: .init(answerSnapshot: [:], answerVersion: 1, scheduledTimeBand: "night", weekday: "tuesday", notificationPermission: "allowed"),
        stimulus: .init(messageId: "test", category: "test", tags: [], treatmentAssigned: "test", assignedProbability: 0.5, policyVersion: "test"))
    row.observe(.responded, at: now.addingTimeInterval(-75))
    row.closeObservationWindow(at: now.addingTimeInterval(-50))
    return row
}
func f(_ rows: [ManagerBenchCase], _ consent: Bool = true) -> ManagerHistoryFeatures? {
    ManagerHistoryFeatures.build(cases: rows, personId: "p", before: now, hasResearchConsent: consent)
}
let good = fixture("1")
precondition(f([good]) == .init(closedCases: 1, observedResponses: 1, positiveResponses: 1))
precondition(f([good], false) == nil)
precondition(f([fixture("2", "other")])?.closedCases == 0)
var future = fixture("3"); future.observationWindowClosedAt = now
precondition(f([future])?.closedCases == 0)
var open = fixture("4"); open.observationWindowClosedAt = nil
precondition(f([open])?.closedCases == 0)
var unknown = fixture("5"); unknown.response.responded = nil; unknown.response.respondedAt = nil
precondition(f([unknown]) == .init(closedCases: 1, observedResponses: 0, positiveResponses: 0))
var negative = fixture("6"); negative.response.responded = false; negative.response.respondedAt = nil
precondition(f([negative]) == .init(closedCases: 1, observedResponses: 1, positiveResponses: 0))
precondition(f([good, good])?.closedCases == 0)
var late = fixture("7"); late.response.respondedAt = now.addingTimeInterval(-10)
precondition(f([late])?.observedResponses == 0)
var invalid = fixture("8"); invalid.stimulus.assignedProbability = 0
precondition(f([invalid])?.closedCases == 0)
print("10/10 synthetic assertions pass; actual ManagerBenchCase source, macOS Swift CLI; no iOS device or consent integration")
