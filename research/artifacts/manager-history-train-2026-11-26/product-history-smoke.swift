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
// Old records have a nominal window end but no actual availability time.
var legacy = good; legacy.outcomeAvailableAt = nil
precondition(f([legacy])?.closedCases == 0)
var delayed = fixture("9"); delayed.observationWindowClosedAt = nil
delayed.closeObservationWindow(at: now.addingTimeInterval(1))
precondition(delayed.observationWindowClosedAt == now.addingTimeInterval(-50))
precondition(delayed.outcomeAvailableAt == now.addingTimeInterval(1))
precondition(f([delayed])?.closedCases == 0)
var correction = fixture("10")
correction.observe(.saved, at: now.addingTimeInterval(-70), recordedAt: now)
precondition(correction.outcomeAvailableAt == now)
precondition(f([correction])?.closedCases == 0)
var unknownCorrection = fixture("11")
unknownCorrection.observe(.saved, at: now.addingTimeInterval(-70))
precondition(unknownCorrection.outcomeAvailableAt == nil)
let roundtrip = try! ManagerBenchCase.decoder.decode(ManagerBenchCase.self, from: ManagerBenchCase.encoder.encode(delayed))
precondition(roundtrip.outcomeAvailableAt == delayed.outcomeAvailableAt)
let oldData = try! ManagerBenchCase.encoder.encode(legacy)
precondition(try! ManagerBenchCase.decoder.decode(ManagerBenchCase.self, from: oldData).outcomeAvailableAt == nil)
print("19/19 synthetic assertions pass; actual mobile model and history source; macOS Swift CLI, no iOS device or consent integration")
